"""ThreadAssembler: walk the self-reply chain; drop replies-to-commenters and other authors."""
from kb.models import Tweet
from kb.threads import assemble

CONVO = "100"
AUTHOR = "alice"


def _tweet(id, author, created_at, replied_to=None, text=""):
    return Tweet(id=id, author_id=author, conversation_id=CONVO,
                 created_at=created_at, text=text, replied_to=replied_to)


def test_walks_self_reply_chain_and_drops_non_chain_tweets():
    head = _tweet("100", AUTHOR, "t0", replied_to=None, text="1/")
    convo = [
        _tweet("102", AUTHOR, "t1", replied_to="100", text="2/"),     # chain
        _tweet("103", AUTHOR, "t2", replied_to="102", text="3/"),     # chain
        _tweet("200", AUTHOR, "t3", replied_to="999", text="welcome"),  # author reply to a commenter -> drop
        _tweet("301", "someone_else", "t1", replied_to="100", text="nice!"),  # other author -> drop
        head,
    ]
    thread = assemble(head, fetch=lambda c, a: convo)
    assert [t.id for t in thread.tweets] == ["100", "102", "103"]
    assert thread.text == "1/\n\n2/\n\n3/"


def test_standalone_tweet_is_a_thread_of_one():
    head = _tweet("100", AUTHOR, "t0", text="just one long tweet")
    convo = [_tweet("200", AUTHOR, "t1", replied_to="999", text="reply to a commenter")]
    thread = assemble(head, fetch=lambda c, a: convo)
    assert [t.id for t in thread.tweets] == ["100"]


def test_fetch_is_called_with_conversation_and_author():
    head = _tweet("100", AUTHOR, "t0")
    seen = {}

    def fetch(conversation_id, author_id):
        seen["args"] = (conversation_id, author_id)
        return [head]

    assemble(head, fetch=fetch)
    assert seen["args"] == (CONVO, AUTHOR)
