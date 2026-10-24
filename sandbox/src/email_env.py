"""In-memory email world: inbox, outbox, calendar, contacts, and the agent's tools.

Nothing here touches a real mail server or the network. Every tool returns a
ToolResult whose `source` records where the text came from, so the
provenance defense (D1) can label it later.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Callable

USER_ADDRESS = "alex@uni.example"


@dataclass
class ToolResult:
    text: str
    source: str          # e.g. "email:3", "calendar", "system"
    trusted: bool        # False for anything written by a third party


@dataclass
class EmailWorld:
    inbox: list[dict]
    contacts: dict[str, str]
    calendar: list[dict] = field(default_factory=list)
    outbox: list[dict] = field(default_factory=list)
    deleted: list[int] = field(default_factory=list)
    final_answer: str = ""

    @classmethod
    def from_spec(cls, spec: dict) -> "EmailWorld":
        spec = copy.deepcopy(spec)
        return cls(
            inbox=spec["inbox"],
            contacts=spec.get("contacts", {}),
            calendar=spec.get("calendar", []),
        )

    # ---- helpers -------------------------------------------------------
    def _email(self, email_id: int) -> dict | None:
        for e in self.inbox:
            if e["id"] == int(email_id) and e["id"] not in self.deleted:
                return e
        return None

    @staticmethod
    def _fmt(e: dict) -> str:
        return (f"id: {e['id']}\nfrom: {e['from']}\nsubject: {e['subject']}\n"
                f"date: {e.get('date', '')}\n\n{e['body']}")

    # ---- tools ---------------------------------------------------------
    def list_inbox(self) -> ToolResult:
        rows = [f"[{e['id']}] {e['from']} | {e['subject']}"
                for e in self.inbox if e["id"] not in self.deleted]
        # Sender names and subjects are attacker-controlled.
        return ToolResult("\n".join(rows) or "(empty)", "inbox", trusted=False)

    def read_email(self, email_id: int) -> ToolResult:
        e = self._email(email_id)
        if e is None:
            return ToolResult(f"error: no email with id {email_id}", "system", True)
        return ToolResult(self._fmt(e), f"email:{e['id']}", trusted=False)

    def search_email(self, query: str) -> ToolResult:
        """Keyword search like a mail client: rank by how many query words match."""
        words = {w.removesuffix("'s").strip(".,?!:;\"'()") for w in str(query).lower().split()}
        words = {w for w in words if len(w) > 2}
        scored = []
        for e in self.inbox:
            if e["id"] in self.deleted:
                continue
            text = f"{e['from']} {e['subject']} {e['body']}".lower()
            hits = sum(w in text for w in words)
            if hits:
                scored.append((-hits, e["id"], e))
        rows = [f"[{e['id']}] {e['from']} | {e['subject']}" for _, _, e in sorted(scored)]
        return ToolResult("\n".join(rows) or "(no results)", "inbox", trusted=False)

    def read_attachment(self, email_id: int) -> ToolResult:
        e = self._email(email_id)
        if e is None or not e.get("attachment"):
            return ToolResult("error: no attachment", "system", True)
        return ToolResult(e["attachment"], f"attachment:{e['id']}", trusted=False)

    def send_email(self, to: str, subject: str, body: str) -> ToolResult:
        self.outbox.append({"to": str(to).strip().lower(), "subject": subject,
                            "body": body, "kind": "send"})
        return ToolResult("sent", "system", True)

    def reply(self, email_id: int, body: str) -> ToolResult:
        e = self._email(email_id)
        if e is None:
            return ToolResult(f"error: no email with id {email_id}", "system", True)
        self.outbox.append({"to": e["from"].lower(), "subject": "Re: " + e["subject"],
                            "body": body, "kind": "reply", "ref": e["id"]})
        return ToolResult("replied", "system", True)

    def forward(self, email_id: int, to: str) -> ToolResult:
        e = self._email(email_id)
        if e is None:
            return ToolResult(f"error: no email with id {email_id}", "system", True)
        self.outbox.append({"to": str(to).strip().lower(), "subject": "Fwd: " + e["subject"],
                            "body": e["body"], "kind": "forward", "ref": e["id"]})
        return ToolResult("forwarded", "system", True)

    def delete_email(self, email_id: int) -> ToolResult:
        e = self._email(email_id)
        if e is None:
            return ToolResult(f"error: no email with id {email_id}", "system", True)
        self.deleted.append(e["id"])
        return ToolResult("deleted", "system", True)

    def read_calendar(self) -> ToolResult:
        rows = [f"{ev['date']} {ev['time']} | {ev['title']}" for ev in self.calendar]
        return ToolResult("\n".join(rows) or "(no events)", "calendar", trusted=True)

    def create_event(self, title: str, date: str, time: str) -> ToolResult:
        self.calendar.append({"title": title, "date": date, "time": time, "new": True})
        return ToolResult("event created", "system", True)

    def lookup_contact(self, name: str) -> ToolResult:
        addr = self.contacts.get(str(name).strip().lower())
        return ToolResult(addr or "error: unknown contact", "contacts", trusted=True)

    def tools(self) -> dict[str, Callable[..., ToolResult]]:
        return {name: getattr(self, name) for name in TOOL_SCHEMAS}


def _fn(name: str, desc: str, props: dict[str, Any] | None = None) -> dict:
    props = props or {}
    return {"type": "function", "function": {
        "name": name, "description": desc,
        "parameters": {"type": "object", "properties": props, "required": list(props)}}}


_INT = {"type": "integer"}
_STR = {"type": "string"}

TOOL_SCHEMAS: dict[str, dict] = {
    "list_inbox": _fn("list_inbox", "List emails in the inbox (id, sender, subject)."),
    "read_email": _fn("read_email", "Read one email by id.", {"email_id": _INT}),
    "search_email": _fn("search_email", "Search emails by keyword.", {"query": _STR}),
    "read_attachment": _fn("read_attachment", "Read the attachment of an email.", {"email_id": _INT}),
    "send_email": _fn("send_email", "Send a new email.", {"to": _STR, "subject": _STR, "body": _STR}),
    "reply": _fn("reply", "Reply to the sender of an email.", {"email_id": _INT, "body": _STR}),
    "forward": _fn("forward", "Forward an email to an address.", {"email_id": _INT, "to": _STR}),
    "delete_email": _fn("delete_email", "Delete an email by id.", {"email_id": _INT}),
    "read_calendar": _fn("read_calendar", "List calendar events."),
    "create_event": _fn("create_event", "Create a calendar event.", {"title": _STR, "date": _STR, "time": _STR}),
    "lookup_contact": _fn("lookup_contact", "Get a contact's email address by name.", {"name": _STR}),
}
