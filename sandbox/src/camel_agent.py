"""A CAMEL-AI agent behind our gate (consultation 30 Oct: "incorporate camel ai into our sandbox").

CAMEL-AI (camel-ai.org, pip package camel-ai) is an open-source multi-agent framework. Here its ChatAgent
replaces our own loop (agent.py); everything else is unchanged:
  * model: GatewayBackend, a CAMEL model backend that forwards each call to our llm.py client, so the
    model, num_ctx, temperature and think=false are those of every other run, and the only network path
    is still the nginx gateway;
  * tools: each EmailWorld tool is a CAMEL FunctionTool whose body is the unchanged gate from defenses.py
    (visible_tools, check, observe), with the same neutral refusals and the same call log as agent.py,
    so scoring, diagnostics and demo.py work as they are.
Not to be confused with CaMeL (Debenedetti et al., 2025), a defense; see the report.

Same signature and return value as agent.run_episode. B1 is not supported: it rewires the planner.
"""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
import warnings

from agent import EPISODE_TIMEOUT_S, MAX_STEPS, MAX_TOOL_CHARS, SYSTEM_PROMPT
from email_env import TOOL_SCHEMAS, ToolResult

from camel.agents import ChatAgent
from camel.logger import disable_logging
from camel.models import BaseModelBackend
from camel.toolkits import FunctionTool
from camel.types import ModelType
from camel.utils import OpenAITokenCounter
from openai.types.chat import ChatCompletion

warnings.filterwarnings("ignore", module="camel")  # e.g. 'parameter description is missing'
disable_logging()  # CAMEL can log message text; progress output stays ids and booleans only
logging.getLogger("camel").setLevel(logging.CRITICAL)
NUM_CTX = int(os.environ.get("NUM_CTX", "16384"))


class EpisodeTimeout(Exception):
    pass


def to_ollama(messages: list[dict]) -> list[dict]:
    """CAMEL's OpenAI-format history -> the Ollama /api/chat format llm.py sends."""
    out = []
    for m in messages:
        msg = {"role": m["role"], "content": m.get("content") or ""}
        if not isinstance(msg["content"], str):  # list of content parts
            msg["content"] = "".join(p.get("text", "") for p in msg["content"] if isinstance(p, dict))
        if m.get("tool_calls"):
            msg["tool_calls"] = [{"function": {"name": c["function"]["name"],
                                               "arguments": _args(c["function"].get("arguments"))}}
                                 for c in m["tool_calls"]]
        out.append(msg)
    return out


def _args(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}


def to_completion(out: dict, model: str) -> ChatCompletion:
    """llm.py's reply -> the OpenAI ChatCompletion CAMEL expects."""
    msg = out["message"]
    calls = [{"id": f"call_{uuid.uuid4().hex[:12]}", "type": "function",
              "function": {"name": c.get("function", {}).get("name", ""),
                           "arguments": json.dumps(_args(c.get("function", {}).get("arguments")))}}
             for c in msg.get("tool_calls") or []]
    return ChatCompletion.model_validate({
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}", "object": "chat.completion", "created": int(time.time()),
        "model": model,
        "choices": [{"index": 0, "finish_reason": "tool_calls" if calls else "stop",
                     "message": {"role": "assistant", "content": msg.get("content") or "",
                                 "tool_calls": calls or None}}],
        "usage": {"prompt_tokens": out["prompt_tokens"], "completion_tokens": out["completion_tokens"],
                  "total_tokens": out["prompt_tokens"] + out["completion_tokens"]}})


class GatewayBackend(BaseModelBackend):
    """CAMEL model backend over llm.py. Only the tools the gate makes visible are offered to the model."""

    def __init__(self, llm, log: dict, visible: list[str], start: float):
        super().__init__(getattr(llm, "model", "scripted"), {},
                         token_counter=OpenAITokenCounter(ModelType.GPT_4O_MINI))
        self.llm, self.log, self.visible, self.start = llm, log, set(visible), start
        self.last_had_calls = False

    @property
    def token_counter(self):
        return self._token_counter

    @property
    def token_limit(self) -> int:
        return NUM_CTX

    def _run(self, messages, response_format=None, tools=None):
        if time.monotonic() - self.start > EPISODE_TIMEOUT_S:
            raise EpisodeTimeout
        tools = [t for t in tools or [] if t.get("function", {}).get("name") in self.visible]
        out = self.llm(to_ollama(messages), tools or None)
        self.log["llm_calls"] += 1
        self.log["prompt_tokens"] += out["prompt_tokens"]
        self.log["completion_tokens"] += out["completion_tokens"]
        self.last_had_calls = bool(out["message"].get("tool_calls"))
        return to_completion(out, self.model_type)

    async def _arun(self, messages, response_format=None, tools=None):
        return self._run(messages, response_format, tools)


def gated_tools(task, world, defense, log, user_msgs, visible) -> list[FunctionTool]:
    """Every EmailWorld tool as a CAMEL FunctionTool whose body is the gate (as agent._run_turn)."""
    tools = world.tools()

    def make(name):
        def call(**args):
            ctx = {"task": task, "world": world, "messages": user_msgs}
            args = defense.resolve_args(args)
            decision = defense.check(name, args, ctx)
            reason = ""  # which rule fired (fixed strings from defenses.py, never model text)
            if name not in visible:  # hidden by the task's allowlist (the model was never shown it)
                log["blocked"] += 1
                reason = "tool hidden by the task's allowlist"
                result = ToolResult(f"error: tool '{name}' is not available", "system", True)
            elif not decision.allowed:
                log["blocked"] += 1
                reason = decision.reason
                result = ToolResult("error: action not permitted by policy", "system", True)
            else:
                try:
                    result = tools[name](**args)
                except (TypeError, ValueError) as exc:
                    result = ToolResult(f"error: bad arguments ({exc})", "system", True)
            defense.observe(name, result, ctx)
            result = defense.transform(name, result, ctx)
            log["calls"].append({"tool": name, "args": args, "allowed": name in visible and decision.allowed,
                                 **({"reason": reason} if reason else {})})
            return result.text[:MAX_TOOL_CHARS]
        call.__name__ = name
        call.__doc__ = TOOL_SCHEMAS[name]["function"]["description"]
        return FunctionTool(call, openai_tool_schema=TOOL_SCHEMAS[name])
    return [make(n) for n in tools]


def run_camel_episode(task: dict, world, llm, defense) -> dict:
    """One episode with a CAMEL-AI ChatAgent; `task["turns"]` are further user messages in the same chat."""
    if getattr(defense, "name", "") == "b1":
        raise ValueError("B1 (Dual-LLM) rewires the planner and is not run with the CAMEL agent")
    start = time.monotonic()
    log = {"calls": [], "blocked": 0, "prompt_tokens": 0, "completion_tokens": 0, "llm_calls": 0,
           "outcome": "finished", "agent": "camel"}
    visible = defense.visible_tools(task, list(world.tools()))
    user_msgs: list[dict] = []
    backend = GatewayBackend(llm, log, visible, start)
    agent = ChatAgent(system_message=SYSTEM_PROMPT + defense.system_note(), model=backend,
                      tools=gated_tools(task, world, defense, log, user_msgs, visible),
                      max_iteration=MAX_STEPS, retry_attempts=1)
    answers = []
    for prompt in [task["user_prompt"], *task.get("turns", [])]:
        user_msgs.append({"role": "user", "content": prompt})
        try:
            resp = agent.step(prompt)
        except EpisodeTimeout:
            log["outcome"] = "timeout"
            break
        except Exception as exc:  # model error inside CAMEL (network, timeout, bad reply)
            cause = exc.__cause__ or exc
            log["outcome"] = "timeout" if isinstance(cause, EpisodeTimeout) else f"llm_error:{type(cause).__name__}"
            break
        if backend.last_had_calls:  # stopped by max_iteration while still calling tools
            log["outcome"] = "step_cap"
            break
        answers.append(resp.msgs[0].content if resp.msgs else "")
    world.final_answer = defense.render("\n".join(a for a in answers if a))
    log["seconds"] = round(time.monotonic() - start, 2)
    log["transcript"] = [{"role": m.get("role"), "content": m.get("content")}
                         for m in (agent.memory.get_context()[0] if agent.memory else [])]
    return log
