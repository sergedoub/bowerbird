"""ThreadAssembler — reconstruct a self-thread from a conversation search.

Spike findings (PRD #1):
  - a `conversation_id:` search returns the WHOLE conversation (other people's replies too);
  - the same author may post replies to *commenters* in that conversation, which are NOT
    part of the self-thread.

So we don't just keep the author's tweets — we walk the **self-reply chain**: starting at the
head, repeatedly follow the author tweet whose `replied_to` points at the previous link. A
standalone tweet (nobody self-replied) correctly yields a thread of one.

The fetch is injected, so the stitching logic is unit-testable with no network. The injected
fetch is expected to run an app-only `conversation_id:<id> from:<author_id>` search and return
Tweets carrying `replied_to`.
"""
from __future__ import annotations

from collections.abc import Callable

from .models import Thread, Tweet

# fetch(conversation_id, author_id) -> author's tweets in that conversation
FetchConversation = Callable[[str, str], list[Tweet]]


def assemble(head: Tweet, fetch: FetchConversation) -> Thread:
    convo = fetch(head.conversation_id, head.author_id)
    own = {t.id: t for t in convo if t.author_id == head.author_id}
    own[head.id] = head  # always include the head, even if search omitted it

    children: dict[str, list[Tweet]] = {}
    for t in own.values():
        if t.replied_to:
            children.setdefault(t.replied_to, []).append(t)

    chain = [head]
    seen = {head.id}
    cur = head
    while True:
        nexts = sorted(
            (c for c in children.get(cur.id, []) if c.id not in seen),
            key=lambda t: (t.created_at, t.id),
        )
        if not nexts:
            break
        cur = nexts[0]  # if the author self-replied more than once, follow the earliest
        chain.append(cur)
        seen.add(cur.id)

    return Thread(
        head_id=head.id,
        author_id=head.author_id,
        conversation_id=head.conversation_id,
        tweets=tuple(chain),
    )
