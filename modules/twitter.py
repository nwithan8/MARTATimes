from typing import List, Tuple


def can_add_to_tweet(existing_text: str, text_to_add: str) -> bool:
    """
    Checks if adding text_to_add to existing_text will exceed Twitter's 280-character limit
    """
    if len(existing_text) + len(text_to_add) > 280:
        return False
    return True


def add_as_many_as_possible_to_tweet(starting_text: str, items: List[str]) -> Tuple[str, List[str]]:
    """
    Adds as many items to the starting_text as possible, returning the updated text and the remaining items
    """
    updated_text: str = starting_text
    remaining_items: List[str] = items
    for item in items:
        if can_add_to_tweet(existing_text=updated_text, text_to_add=item):
            updated_text += item
            remaining_items.remove(item)
        else:
            break
    return updated_text, remaining_items
