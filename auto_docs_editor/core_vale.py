from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from loguru import logger

from settings import MODEL_NAME
from utils import get_langfuse_handler


def enforce_vale_style(document_path: Path, max_retries: int = 5) -> None:
    """Iteratively run Vale and use an LLM to fix the errors."""
    if not shutil.which("vale"):
        logger.error("Vale is not installed or not in PATH. Skipping Vale enforcement.")
        return

    llm = ChatOpenAI(model=MODEL_NAME, temperature=0)

    callbacks = []
    handler = get_langfuse_handler()
    if handler:
        callbacks.append(handler)

    prompt_template = ChatPromptTemplate.from_template(
        "You are a technical editor. I will provide you with a markdown document and a list of style errors found by Vale (Google Style Guide).\n"
        "Your task is to fix the style errors in the document. \n"
        "If a Vale error is too pedantic, false positive, or makes the text worse/awkward, you may ignore it.\n"
        "If you determine that ALL remaining errors are pedantic or should be ignored, strictly output the single word: PEDANTIC\n"
        "Otherwise, output the FULL corrected markdown document. Do not include any markdown fences (like ```markdown) or conversational text.\n\n"
        "Errors:\n{errors}\n\n"
        "Document:\n{document}"
    )

    # Initialize chain properly with prompt | llm | parser
    chain = prompt_template | llm | StrOutputParser()

    for attempt in range(1, max_retries + 1):
        logger.info(f"[Vale] Enforcement attempt {attempt}/{max_retries}...")

        # Run Vale
        try:
            result = subprocess.run(
                ["vale", "--output=line", str(document_path)],
                capture_output=True,
                text=True,
                check=False,
            )
        except Exception as e:
            logger.error(f"[Vale] Failed to run vale: {e}")
            return

        # Parse line output
        output_lines = result.stdout.strip().splitlines()

        file_errors = []
        for line in output_lines:
            parts = line.split(":", 4)
            if len(parts) >= 5:
                line_num = parts[1]
                check = parts[3]
                message = parts[4]
                file_errors.append(
                    {"Line": line_num, "Message": message.strip(), "Check": check, "Match": "N/A"}
                )

        if not file_errors:
            logger.success("[Vale] No errors found!")
            break

        # Filter/Format errors for the LLM
        error_list = []
        for err in file_errors:
            line = err.get("Line")
            msg = err.get("Message")
            rule = err.get("Check")
            error_list.append(f"- Line {line}: {msg} (Rule: {rule})")

        formatted_errors = "\n".join(error_list)
        logger.info(f"[Vale] Found {len(error_list)} errors:\n{formatted_errors}")

        current_text = document_path.read_text(encoding="utf-8")

        # Ask LLM to fix
        # Standardized invocation: pass callbacks in config
        response = chain.invoke(
            {"errors": formatted_errors, "document": current_text}, config={"callbacks": callbacks}
        )

        if response.strip() == "PEDANTIC":
            logger.info("[Vale] LLM determined remaining errors are pedantic. Stopping.")
            break

        # Heuristic check: if response is drastically shorter, something might be wrong
        if len(response) < len(current_text) * 0.5:
            logger.warning(
                "[Vale] LLM response seems too short. Aborting this step to prevent data loss."
            )
            break

        # Apply changes
        if response != current_text:
            document_path.write_text(response, encoding="utf-8")
            logger.success("[Vale] Applied fixes from LLM.")
        else:
            logger.info("[Vale] LLM proposed no changes. Stopping.")
            break
    else:
        logger.warning("[Vale] Max retries reached. Some errors may remain.")
