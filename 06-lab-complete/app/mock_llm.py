def ask(question: str, history: list[dict] | None = None) -> str:
    history = history or []
    previous_turns = len(history)
    return (
        "Mock answer: "
        f"I received your question '{question}'. "
        f"Conversation context has {previous_turns} previous messages."
    )