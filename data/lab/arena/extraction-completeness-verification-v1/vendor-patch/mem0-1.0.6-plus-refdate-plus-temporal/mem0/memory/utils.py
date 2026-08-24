import hashlib
import re

from mem0.configs.prompts import (
    FACT_RETRIEVAL_PROMPT,
    USER_MEMORY_EXTRACTION_PROMPT,
    AGENT_MEMORY_EXTRACTION_PROMPT,
)


#: ARENA PATCH (hindsight-archaeology-v1 / arena-mem0-base-plus-x-v1) --
#: both extraction prompts hardcode "Today's date is {datetime.now():%Y-%m-%d}."
#: as a module-level f-string, evaluated once at import time. For a corpus of
#: 2022/2023-dated conversations ingested by a process that started in 2026,
#: this anchors every relative-time expression ("yesterday", "next week") to
#: the wrong real-world date, and there was previously no way to override it
#: per call. `_with_reference_date` does a plain string substitution against
#: that fixed line so a caller-supplied historical date can ground extraction
#: instead. No other change to either prompt's wording or instructions.
_TODAYS_DATE_LINE = re.compile(r"Today's date is \d{4}-\d{2}-\d{2}\.")


def _with_reference_date(prompt: str, reference_date):
    if not reference_date:
        return prompt
    return _TODAYS_DATE_LINE.sub(f"Today's date is {reference_date}.", prompt)


#: ARENA PATCH (event-time-resolution-calibration-v1) -- calibrates a second,
#: separate treatment on top of PER_SESSION_REFERENCE_DATE_AT_EXTRACTION. That
#: earlier patch supplies a correct reference_date but no instruction to use
#: it; calibration confirmed it is inert (relative expressions like "today"
#: are preserved verbatim in extracted facts, see
#: data/lab/arena/base-plus-x-v1/calibration-per-session-reference-date.json).
#: This adds exactly one instruction bullet, inserted immediately after the
#: "Today's date is ..." line, telling the model to resolve relative time
#: expressions against that date when unambiguous and to never fabricate one
#: otherwise. No other wording changes; no few-shot examples added.
_TEMPORAL_RESOLUTION_INSTRUCTION = (
    "- When a fact contains a relative time expression such as \"today\", "
    "\"yesterday\", \"tomorrow\", \"last month\", or \"next year\", resolve it "
    "against the reference date above and store the fact with the "
    "corresponding absolute date whenever this can be done unambiguously. "
    "Do not invent a date when the text does not provide enough temporal "
    "information."
)
_TODAYS_DATE_BULLET_LINE = re.compile(r"^- Today's date is \d{4}-\d{2}-\d{2}\.$", re.MULTILINE)


def _with_temporal_resolution_instruction(prompt: str, enabled: bool) -> str:
    if not enabled:
        return prompt
    return _TODAYS_DATE_BULLET_LINE.sub(
        lambda m: f"{m.group(0)}\n{_TEMPORAL_RESOLUTION_INSTRUCTION}", prompt, count=1)


#: ARENA PATCH (extraction-completeness-verification-v1) -- after Mem0's
#: normal extraction call returns new_retrieved_facts, an optional second LLM
#: call re-reads the original text against what was already extracted and
#: finds two distinct kinds of completeness gaps: (a) MISSING -- a standalone
#: fact stated in the text but absent from the extracted list entirely, and
#: (b) BUNDLED -- an already-extracted fact that merges multiple distinct
#: enumerable items into one fact string, which the existing few-shot
#: examples (see USER_MEMORY_EXTRACTION_PROMPT's Inception/Interstellar
#: example, which merges two favourite movies into one fact string) currently
#: teach the model to do. An earlier version of this prompt asked only about
#: "omitted" facts, which calibration showed is worded too narrowly to catch
#: (b): every individual item in a bundled fact is technically already
#: present -- textually, inside the merged string -- so nothing reads as
#: "missing," and the check came back empty on every clean-merge calibration
#: case (data/lab/arena/extraction-completeness-verification-v1/
#: calibration.json, first run). This version asks for both explicitly and
#: returns a replace-and-add structure rather than an additive-only list, so
#: a bundled fact can be split rather than merely supplemented. Called from
#: main.py only when metadata["completeness_check_enabled"] is truthy; every
#: other call site is unaffected -- this function is additive, not a
#: modification of get_fact_retrieval_messages or either extraction prompt.
def get_completeness_check_messages(parsed_messages, already_extracted_facts):
    facts_block = "\n".join(f"- {f}" for f in already_extracted_facts) or "(none)"
    system_prompt = (
        "You are auditing a fact-extraction step for completeness. You will be "
        "given the original conversation text and the facts already extracted "
        "from it. Find two kinds of gaps:\n"
        "(1) MISSING: a standalone fact about the user stated in the text but "
        "not present in the extracted list at all.\n"
        "(2) BUNDLED: an already-extracted fact that combines multiple "
        "distinct enumerable items (e.g. a list of movies, books, goals, "
        "purchases, or activities) into one fact string, when each item "
        "should have been its own separate fact. For a bundled fact, name "
        "the exact original fact string being replaced and list the "
        "individual facts it should split into.\n"
        "Do not invent anything not stated in the text, and do not report a "
        "fact as missing or bundled if the extracted list already represents "
        "it correctly as separate items. Return your answer as JSON: "
        "{\"facts_to_add\": [\"...\"], \"facts_to_replace\": "
        "[{\"original\": \"...\", \"split_into\": [\"...\", \"...\"]}]}. "
        "Return empty lists for both keys if the extraction is already "
        "complete and correctly split."
    )
    user_prompt = (
        f"Original conversation text:\n{parsed_messages}\n\n"
        f"Facts already extracted:\n{facts_block}\n\n"
        "Find any facts missing entirely, and any already-extracted fact "
        "that bundles multiple distinct items and should be split."
    )
    return system_prompt, user_prompt


def get_fact_retrieval_messages(message, is_agent_memory=False, reference_date=None,
                                 resolve_relative_time=False):
    """Get fact retrieval messages based on the memory type.

    Args:
        message: The message content to extract facts from
        is_agent_memory: If True, use agent memory extraction prompt, else use user memory extraction prompt
        reference_date: ARENA PATCH -- optional 'YYYY-MM-DD' (or any string the
            prompt's few-shot examples don't otherwise constrain) to substitute
            for the prompt's hardcoded "Today's date is ...". None preserves the
            original, unpatched behavior exactly.
        resolve_relative_time: ARENA PATCH (event-time-resolution-calibration-v1)
            -- when True, inserts one explicit instruction telling the model to
            resolve relative time expressions against reference_date. False (the
            default) preserves PER_SESSION_REFERENCE_DATE_AT_EXTRACTION's exact
            behavior with no instruction added.

    Returns:
        tuple: (system_prompt, user_prompt)
    """
    if is_agent_memory:
        prompt = _with_reference_date(AGENT_MEMORY_EXTRACTION_PROMPT, reference_date)
        prompt = _with_temporal_resolution_instruction(prompt, resolve_relative_time)
        return prompt, f"Input:\n{message}"
    else:
        prompt = _with_reference_date(USER_MEMORY_EXTRACTION_PROMPT, reference_date)
        prompt = _with_temporal_resolution_instruction(prompt, resolve_relative_time)
        return prompt, f"Input:\n{message}"


def get_fact_retrieval_messages_legacy(message):
    """Legacy function for backward compatibility."""
    return FACT_RETRIEVAL_PROMPT, f"Input:\n{message}"


def ensure_json_instruction(system_prompt, user_prompt):
    """Ensure the word 'json' appears in the prompts when using json_object response format.

    OpenAI's API requires the word 'json' to appear in the messages when
    response_format is set to {"type": "json_object"}. When users provide a
    custom_fact_extraction_prompt that doesn't include 'json', this causes a
    400 error. This function appends a JSON format instruction to the system
    prompt if 'json' is not already present in either prompt.

    Args:
        system_prompt: The system prompt string
        user_prompt: The user prompt string

    Returns:
        tuple: (system_prompt, user_prompt) with JSON instruction added if needed
    """
    combined = (system_prompt + user_prompt).lower()
    if "json" not in combined:
        system_prompt += (
            "\n\nYou must return your response in valid JSON format "
            "with a 'facts' key containing an array of strings."
        )
    return system_prompt, user_prompt


def parse_messages(messages):
    response = ""
    for msg in messages:
        if msg["role"] == "system":
            response += f"system: {msg['content']}\n"
        if msg["role"] == "user":
            response += f"user: {msg['content']}\n"
        if msg["role"] == "assistant":
            response += f"assistant: {msg['content']}\n"
    return response


def format_entities(entities):
    if not entities:
        return ""

    formatted_lines = []
    for entity in entities:
        simplified = f"{entity['source']} -- {entity['relationship']} -- {entity['destination']}"
        formatted_lines.append(simplified)

    return "\n".join(formatted_lines)


def remove_code_blocks(content: str) -> str:
    """
    Removes enclosing code block markers ```[language] and ``` from a given string.

    Remarks:
    - The function uses a regex pattern to match code blocks that may start with ``` followed by an optional language tag (letters or numbers) and end with ```.
    - If a code block is detected, it returns only the inner content, stripping out the markers.
    - If no code block markers are found, the original content is returned as-is.
    """
    pattern = r"^```[a-zA-Z0-9]*\n([\s\S]*?)\n```$"
    match = re.match(pattern, content.strip())
    match_res=match.group(1).strip() if match else content.strip()
    return re.sub(r"<think>.*?</think>", "", match_res, flags=re.DOTALL).strip()



def extract_json(text):
    """
    Extracts JSON content from a string, removing enclosing triple backticks and optional 'json' tag if present.
    If no code block is found, returns the text as-is.
    """
    text = text.strip()
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        json_str = match.group(1)
    else:
        json_str = text  # assume it's raw JSON
    return json_str


def get_image_description(image_obj, llm, vision_details):
    """
    Get the description of the image
    """

    if isinstance(image_obj, str):
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "A user is providing an image. Provide a high level description of the image and do not include any additional text.",
                    },
                    {"type": "image_url", "image_url": {"url": image_obj, "detail": vision_details}},
                ],
            },
        ]
    else:
        messages = [image_obj]

    response = llm.generate_response(messages=messages)
    return response


def parse_vision_messages(messages, llm=None, vision_details="auto"):
    """
    Parse the vision messages from the messages
    """
    returned_messages = []
    for msg in messages:
        if msg["role"] == "system":
            returned_messages.append(msg)
            continue

        # Handle message content
        if isinstance(msg["content"], list):
            # Multiple image URLs in content
            description = get_image_description(msg, llm, vision_details)
            returned_messages.append({"role": msg["role"], "content": description})
        elif isinstance(msg["content"], dict) and msg["content"].get("type") == "image_url":
            # Single image content
            image_url = msg["content"]["image_url"]["url"]
            try:
                description = get_image_description(image_url, llm, vision_details)
                returned_messages.append({"role": msg["role"], "content": description})
            except Exception:
                raise Exception(f"Error while downloading {image_url}.")
        else:
            # Regular text content
            returned_messages.append(msg)

    return returned_messages


def process_telemetry_filters(filters):
    """
    Process the telemetry filters
    """
    if filters is None:
        return {}

    encoded_ids = {}
    if "user_id" in filters:
        encoded_ids["user_id"] = hashlib.md5(filters["user_id"].encode()).hexdigest()
    if "agent_id" in filters:
        encoded_ids["agent_id"] = hashlib.md5(filters["agent_id"].encode()).hexdigest()
    if "run_id" in filters:
        encoded_ids["run_id"] = hashlib.md5(filters["run_id"].encode()).hexdigest()

    return list(filters.keys()), encoded_ids


def sanitize_relationship_for_cypher(relationship) -> str:
    """Sanitize relationship text for Cypher queries by replacing problematic characters."""
    char_map = {
        "...": "_ellipsis_",
        "…": "_ellipsis_",
        "。": "_period_",
        "，": "_comma_",
        "；": "_semicolon_",
        "：": "_colon_",
        "！": "_exclamation_",
        "？": "_question_",
        "（": "_lparen_",
        "）": "_rparen_",
        "【": "_lbracket_",
        "】": "_rbracket_",
        "《": "_langle_",
        "》": "_rangle_",
        "'": "_apostrophe_",
        '"': "_quote_",
        "\\": "_backslash_",
        "/": "_slash_",
        "|": "_pipe_",
        "&": "_ampersand_",
        "=": "_equals_",
        "+": "_plus_",
        "*": "_asterisk_",
        "^": "_caret_",
        "%": "_percent_",
        "$": "_dollar_",
        "#": "_hash_",
        "@": "_at_",
        "!": "_bang_",
        "?": "_question_",
        "(": "_lparen_",
        ")": "_rparen_",
        "[": "_lbracket_",
        "]": "_rbracket_",
        "{": "_lbrace_",
        "}": "_rbrace_",
        "<": "_langle_",
        ">": "_rangle_",
    }

    # Apply replacements and clean up
    sanitized = relationship
    for old, new in char_map.items():
        sanitized = sanitized.replace(old, new)

    return re.sub(r"_+", "_", sanitized).strip("_")

