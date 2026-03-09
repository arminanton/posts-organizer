from __future__ import annotations

import json
import logging
import lzma
import os
import random
import re
import shutil
import signal
import sys
import tempfile
import time
import unicodedata
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

import google.generativeai as genai
import instaloader
from dotenv import load_dotenv
from PIL import Image


MANUAL_REVIEW = "MANUAL_REVIEW"
VIDEO_POST = "VIDEO_POST"
EMERGENCY_EXIT_CODE = 2

AI_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "per_image_analysis": {
            "type": "array",
            "items": {"type": "string"},
        },
        "ocr_summary": {"type": "string"},
        "dominant_signal": {
            "type": "string",
            "enum": ["visual", "text", "balanced", "uncertain"],
        },
        "combined_analysis": {"type": "string"},
        "title": {"type": "string"},
    },
    "required": [
        "per_image_analysis",
        "ocr_summary",
        "dominant_signal",
        "combined_analysis",
        "title",
    ],
}


@dataclass(slots=True)
class AppConfig:
    gemini_api_key: str
    target_account: str
    ig_username: str | None = None
    ig_session_file: str | None = None
    gemini_model: str = "gemini-1.5-flash"

    base_dir: Path = Path(".")
    organized_dir_name: str = "Organized_Posts"
    manual_dir_name: str = "Needs_Manual_Naming"
    duplicates_dir_name: str = "Duplicates"
    temp_base_dir_name: str = ".tmp_work"

    tracker_file_name: str = "progress.jsonl"
    duplicates_tracker_file_name: str = "duplicates_progress.jsonl"
    master_index_file_name: str = "master_index.txt"
    duplicates_index_file_name: str = "master_duplicates_index.txt"
    error_log_file_name: str = "error.log"
    app_log_file_name: str = "app.log"
    run_state_file_name: str = "run_state.json"

    ai_requests_per_minute: int = 14
    ai_attempts: int = 3
    download_attempts: int = 3
    retry_base_delay_seconds: float = 15.0
    retry_max_delay_seconds: float = 300.0
    instagram_pause_seconds: float = 60.0

    max_ai_images: int = 10
    max_caption_chars_for_ai: int = 1500
    max_filename_length: int = 80
    fetch_comments: bool = True
    save_hashtags_file: bool = True
    save_caption_file: bool = False
    include_json_indexes: bool = True
    save_ai_analysis_json: bool = True
    save_ai_analysis_text: bool = True
    persist_session_every_posts: int = 10

    @classmethod
    def from_env(cls) -> "AppConfig":
        load_dotenv()

        gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
        target_account = os.getenv("TARGET_ACCOUNT", "").strip()
        ig_username = os.getenv("IG_USERNAME", "").strip() or None

        if not gemini_api_key or not target_account:
            raise ValueError(
                "Missing required .env values: GEMINI_API_KEY and TARGET_ACCOUNT."
            )

        def env_str(name: str, default: str) -> str:
            value = os.getenv(name)
            return value.strip() if value and value.strip() else default

        def env_int(name: str, default: int) -> int:
            value = os.getenv(name)
            return int(value) if value and value.strip() else default

        def env_float(name: str, default: float) -> float:
            value = os.getenv(name)
            return float(value) if value and value.strip() else default

        def env_bool(name: str, default: bool) -> bool:
            value = os.getenv(name)
            if value is None or not value.strip():
                return default
            return value.strip().lower() in {"1", "true", "yes", "on"}

        base_dir = Path(env_str("BASE_DIR", ".")).expanduser().resolve()
        session_from_env = os.getenv("IG_SESSION_FILE", "").strip() or None
        if session_from_env:
            ig_session_file = str(Path(session_from_env).expanduser().resolve())
        elif ig_username:
            ig_session_file = str((base_dir / f".ig_session_{ig_username}").resolve())
        else:
            ig_session_file = None

        return cls(
            gemini_api_key=gemini_api_key,
            target_account=target_account,
            ig_username=ig_username,
            ig_session_file=ig_session_file,
            gemini_model=env_str("GEMINI_MODEL", "gemini-1.5-flash"),
            base_dir=base_dir,
            organized_dir_name=env_str("ORGANIZED_DIR", "Organized_Posts"),
            manual_dir_name=env_str("MANUAL_DIR", "Needs_Manual_Naming"),
            duplicates_dir_name=env_str("DUPLICATES_DIR", "Duplicates"),
            temp_base_dir_name=env_str("TEMP_BASE_DIR", ".tmp_work"),
            tracker_file_name=env_str("TRACKER_FILE", "progress.jsonl"),
            duplicates_tracker_file_name=env_str(
                "DUPLICATES_TRACKER_FILE", "duplicates_progress.jsonl"
            ),
            master_index_file_name=env_str("MASTER_INDEX_FILE", "master_index.txt"),
            duplicates_index_file_name=env_str(
                "MASTER_DUPLICATES_INDEX_FILE", "master_duplicates_index.txt"
            ),
            error_log_file_name=env_str("ERROR_LOG_FILE", "error.log"),
            app_log_file_name=env_str("APP_LOG_FILE", "app.log"),
            run_state_file_name=env_str("RUN_STATE_FILE", "run_state.json"),
            ai_requests_per_minute=env_int("AI_REQUESTS_PER_MINUTE", 14),
            ai_attempts=env_int("AI_ATTEMPTS", 3),
            download_attempts=env_int("DOWNLOAD_ATTEMPTS", 3),
            retry_base_delay_seconds=env_float("RETRY_BASE_DELAY_SECONDS", 15.0),
            retry_max_delay_seconds=env_float("RETRY_MAX_DELAY_SECONDS", 300.0),
            instagram_pause_seconds=env_float("INSTAGRAM_PAUSE_SECONDS", 60.0),
            max_ai_images=env_int("MAX_AI_IMAGES", 10),
            max_caption_chars_for_ai=env_int("MAX_CAPTION_CHARS_FOR_AI", 1500),
            max_filename_length=env_int("MAX_FILENAME_LENGTH", 80),
            fetch_comments=env_bool("FETCH_COMMENTS", True),
            save_hashtags_file=env_bool("SAVE_HASHTAGS_FILE", True),
            save_caption_file=env_bool("SAVE_CAPTION_FILE", False),
            include_json_indexes=env_bool("INCLUDE_JSON_INDEXES", True),
            save_ai_analysis_json=env_bool("SAVE_AI_ANALYSIS_JSON", True),
            save_ai_analysis_text=env_bool("SAVE_AI_ANALYSIS_TEXT", True),
            persist_session_every_posts=env_int("PERSIST_SESSION_EVERY_POSTS", 10),
        )

    @property
    def organized_dir(self) -> Path:
        return self.base_dir / self.organized_dir_name

    @property
    def manual_dir(self) -> Path:
        return self.base_dir / self.manual_dir_name

    @property
    def duplicates_dir(self) -> Path:
        return self.base_dir / self.duplicates_dir_name

    @property
    def temp_base_dir(self) -> Path:
        return self.base_dir / self.temp_base_dir_name

    @property
    def tracker_file(self) -> Path:
        return self.base_dir / self.tracker_file_name

    @property
    def duplicates_tracker_file(self) -> Path:
        return self.base_dir / self.duplicates_tracker_file_name

    @property
    def master_index_file(self) -> Path:
        return self.base_dir / self.master_index_file_name

    @property
    def duplicates_index_file(self) -> Path:
        return self.base_dir / self.duplicates_index_file_name

    @property
    def error_log_file(self) -> Path:
        return self.base_dir / self.error_log_file_name

    @property
    def app_log_file(self) -> Path:
        return self.base_dir / self.app_log_file_name

    @property
    def run_state_file(self) -> Path:
        return self.base_dir / self.run_state_file_name


@dataclass(slots=True)
class PostRecord:
    shortcode: str
    title: str
    normalized_title: str
    media_type: str
    date: str
    time: str
    engagement: str
    hashtags: str
    timestamp: float
    folder: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PostRecord":
        return cls(
            shortcode=str(data["shortcode"]),
            title=str(data["title"]),
            normalized_title=str(
                data.get("normalized_title", title_key(str(data["title"])))
            ),
            media_type=str(data.get("media_type", "unknown")),
            date=str(data["date"]),
            time=str(data["time"]),
            engagement=str(data["engagement"]),
            hashtags=str(data.get("hashtags", "")),
            timestamp=float(data["timestamp"]),
            folder=str(data.get("folder", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AITitleResult:
    title: str
    analysis_text: str
    payload: dict[str, Any]

    @property
    def normalized_title(self) -> str:
        if self.title in {MANUAL_REVIEW, VIDEO_POST}:
            return self.title.lower()
        return title_key(self.title)


class GracefulShutdown:
    def __init__(self) -> None:
        self.kill_now = False
        self._signal_count = 0
        signal.signal(signal.SIGINT, self.exit_gracefully)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, signum: int, frame: Any) -> None:
        self._signal_count += 1
        if self._signal_count == 1:
            print(
                "\n[!] Shutdown signal received. The script will stop after the current safe point..."
            )
            self.kill_now = True
            return

        print("\n[!] Emergency abort requested. Exiting immediately.")
        os._exit(EMERGENCY_EXIT_CODE)

    def should_stop(self) -> bool:
        return self.kill_now

    def sleep(self, seconds: float, logger: logging.Logger, reason: str = "") -> bool:
        remaining = max(0.0, seconds)
        while remaining > 0:
            if self.kill_now:
                if reason:
                    logger.warning(
                        "Shutdown requested during %s. Ending wait early.", reason
                    )
                return True
            step = min(1.0, remaining)
            time.sleep(step)
            remaining -= step
        return self.kill_now


class RateLimiter:
    def __init__(self, max_calls: int, period_seconds: float = 60.0) -> None:
        self.max_calls = max_calls
        self.period_seconds = period_seconds
        self.timestamps: deque[float] = deque(maxlen=max_calls)

    def wait(
        self,
        logger: logging.Logger,
        shutdown: GracefulShutdown | None = None,
    ) -> bool:
        if self.max_calls <= 0:
            return False

        now = time.monotonic()
        if len(self.timestamps) == self.max_calls:
            elapsed = now - self.timestamps[0]
            if elapsed < self.period_seconds:
                sleep_for = self.period_seconds - elapsed + 1.0
                logger.info(
                    "AI rate limit reached. Sleeping %.1f seconds to stay within limits.",
                    sleep_for,
                )
                if shutdown:
                    interrupted = shutdown.sleep(
                        sleep_for, logger, "AI rate-limit backoff"
                    )
                    if interrupted:
                        return True
                else:
                    time.sleep(sleep_for)
                now = time.monotonic()

        self.timestamps.append(now)
        return False


class GeminiTitleGenerator:
    def __init__(
        self,
        config: AppConfig,
        logger: logging.Logger,
        shutdown: GracefulShutdown,
    ) -> None:
        genai.configure(api_key=config.gemini_api_key)
        self.model = genai.GenerativeModel(config.gemini_model)
        self.config = config
        self.logger = logger
        self.shutdown = shutdown
        self.rate_limiter = RateLimiter(config.ai_requests_per_minute)

    def generate_title(
        self, image_paths: Sequence[Path], caption: str = ""
    ) -> AITitleResult:
        trimmed_caption = smart_trim_text(
            caption or "", self.config.max_caption_chars_for_ai
        )
        caption_context = ""
        if trimmed_caption:
            caption_context = (
                "\n\nOptional caption context:\n"
                f"{trimmed_caption}\n"
                "Use the caption only as secondary context. Prefer the image content."
            )

        prompt = (
            "Analyze the provided images from a single educational Instagram post.\n\n"
            "Your job is to understand the whole post, not just one image.\n"
            "If multiple images are provided, analyze every image in order and use the "
            "collection of all image meanings together before deciding the title.\n\n"
            "Priorities:\n"
            "1. First, carefully describe the visual concepts, scenes, symbolism, diagrams, "
            "scientific phenomena, abstractions, metaphors, and overall meaning in each image.\n"
            "2. Second, extract and summarize any important text visible inside the images using OCR.\n"
            "3. Then determine which signal should dominate the final interpretation:\n"
            "   - 'visual' when the images are mostly meaningful visual content\n"
            "   - 'text' when the images are mostly text-heavy slides\n"
            "   - 'balanced' when both matter significantly\n"
            "   - 'uncertain' when the content is too vague\n"
            "4. Finally, generate a creative, highly descriptive 6 to 10 word title for the whole post.\n\n"
            "Important title rules:\n"
            "- Use only standard English letters and numbers.\n"
            "- Do not use emojis, slashes, punctuation, or non-Latin scripts.\n"
            "- If the content is too vague, set the title exactly to MANUAL_REVIEW.\n\n"
            "You MUST return valid JSON matching the provided schema."
            f"{caption_context}"
        )

        selected_images = list(image_paths[: self.config.max_ai_images])

        for attempt in range(1, self.config.ai_attempts + 1):
            if self.shutdown.should_stop():
                return AITitleResult(MANUAL_REVIEW, "", {})

            interrupted = self.rate_limiter.wait(self.logger, self.shutdown)
            if interrupted:
                return AITitleResult(MANUAL_REVIEW, "", {})

            try:
                images = [prepare_image_for_gemini(path) for path in selected_images]
                try:
                    response = self.model.generate_content(
                        [prompt] + images,
                        generation_config=genai.GenerationConfig(
                            response_mime_type="application/json",
                            response_schema=AI_RESPONSE_SCHEMA,
                        ),
                    )
                finally:
                    for image in images:
                        try:
                            image.close()
                        except Exception:
                            pass

                data = parse_ai_json_response(getattr(response, "text", ""), self.logger)
                raw_title = str(data.get("title", "") or "")
                title = sanitize_filename(
                    raw_title, max_len=self.config.max_filename_length
                )
                analysis_text = render_ai_analysis_text(data)

                if not title or MANUAL_REVIEW in title.upper():
                    return AITitleResult(MANUAL_REVIEW, analysis_text, data)

                return AITitleResult(title, analysis_text, data)

            except Exception:
                sleep_for = calculate_retry_delay(
                    attempt=attempt,
                    base=self.config.retry_base_delay_seconds,
                    maximum=self.config.retry_max_delay_seconds,
                )
                self.logger.exception(
                    "AI title generation failed on attempt %s/%s. Sleeping %.1fs.",
                    attempt,
                    self.config.ai_attempts,
                    sleep_for,
                )
                if attempt < self.config.ai_attempts:
                    interrupted = self.shutdown.sleep(
                        sleep_for, self.logger, "AI retry backoff"
                    )
                    if interrupted:
                        return AITitleResult(MANUAL_REVIEW, "", {})

        return AITitleResult(MANUAL_REVIEW, "", {})


def setup_logging(config: AppConfig) -> logging.Logger:
    config.base_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("ig_organizer")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S"
    )

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    app_file_handler = logging.FileHandler(config.app_log_file, encoding="utf-8")
    app_file_handler.setFormatter(formatter)

    error_file_handler = logging.FileHandler(config.error_log_file, encoding="utf-8")
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(formatter)

    logger.addHandler(stream_handler)
    logger.addHandler(app_file_handler)
    logger.addHandler(error_file_handler)
    logger.propagate = False
    return logger


def sanitize_filename(name: str, max_len: int = 80) -> str:
    normalized = (
        unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    )
    cleaned = re.sub(r"[^A-Za-z0-9 _-]", "", normalized)
    cleaned = re.sub(r"\s+", "_", cleaned).strip("._-")
    cleaned = re.sub(r"_+", "_", cleaned)
    return cleaned[:max_len] or "UNTITLED"


def title_key(title: str) -> str:
    normalized = (
        unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    )
    return re.sub(r"[^a-z0-9]+", "", normalized.lower())


def calculate_retry_delay(attempt: int, base: float, maximum: float) -> float:
    raw = min(base * (2 ** (attempt - 1)), maximum)
    return raw + random.uniform(0.0, 2.0)


def smart_trim_text(text: str, max_len: int) -> str:
    text = text.strip()
    if len(text) <= max_len:
        return text
    candidate = text[: max_len + 1]
    split_at = candidate.rfind(" ")
    if split_at > max_len // 2:
        return candidate[:split_at].rstrip()
    return text[:max_len].rstrip()


def strip_json_fences(raw_text: str) -> str:
    cleaned = (raw_text or "").strip()
    if not cleaned:
        return "{}"

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    cleaned = re.sub(r"^json\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip()

    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        cleaned = cleaned[first_brace : last_brace + 1]

    return cleaned or "{}"


def parse_ai_json_response(raw_text: str, logger: logging.Logger) -> dict[str, Any]:
    candidates = [raw_text or "", strip_json_fences(raw_text or "")]

    for candidate in candidates:
        if not candidate.strip():
            continue
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            continue

    logger.warning("AI did not return parseable JSON. Falling back to MANUAL_REVIEW.")
    return {}


def prepare_image_for_gemini(path: Path) -> Image.Image:
    with Image.open(path) as original:
        original.load()
        if original.mode not in {"RGB", "L"}:
            normalized = original.convert("RGB")
            return normalized.copy()
        return original.copy()


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        delete=False,
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
    ) as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
        temp_name = handle.name
    os.replace(temp_name, path)


def atomic_write_json(path: Path, payload: Any) -> None:
    content = json.dumps(payload, indent=2, ensure_ascii=False)
    atomic_write_text(path, content + "\n")


def append_jsonl(path: Path, item: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def safe_rmtree(path: Path, logger: logging.Logger) -> None:
    if not path.exists():
        return
    try:
        shutil.rmtree(path)
    except Exception:
        logger.exception("Failed to remove temporary directory: %s", path)


def workspace_for_shortcode(config: AppConfig, shortcode: str) -> Path:
    return config.temp_base_dir / shortcode


def create_or_reuse_post_workspace(config: AppConfig, shortcode: str) -> Path:
    config.temp_base_dir.mkdir(parents=True, exist_ok=True)
    workspace = workspace_for_shortcode(config, shortcode)
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def ensure_directories(config: AppConfig) -> None:
    config.organized_dir.mkdir(parents=True, exist_ok=True)
    config.manual_dir.mkdir(parents=True, exist_ok=True)
    config.duplicates_dir.mkdir(parents=True, exist_ok=True)
    config.temp_base_dir.mkdir(parents=True, exist_ok=True)


def load_tracker(
    tracker_path: Path,
    processed_shortcodes: set[str],
    processed_titles: set[str] | None,
    logger: logging.Logger,
) -> list[PostRecord]:
    records_by_shortcode: dict[str, PostRecord] = {}

    if tracker_path.exists():
        logger.info("Loading tracker: %s", tracker_path)
        with open(tracker_path, "r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                raw = line.strip()
                if not raw:
                    continue
                try:
                    data = json.loads(raw)
                    record = PostRecord.from_dict(data)
                    records_by_shortcode[record.shortcode] = record
                except Exception:
                    logger.exception(
                        "Skipping malformed tracker line %s in %s",
                        line_number,
                        tracker_path,
                    )

    records = sorted(records_by_shortcode.values(), key=lambda item: item.timestamp)

    for record in records:
        processed_shortcodes.add(record.shortcode)
        if (
            processed_titles is not None
            and record.title not in {MANUAL_REVIEW, VIDEO_POST}
        ):
            processed_titles.add(record.normalized_title)

    if records:
        rewrite_tracker(tracker_path, records)
    return records


def rewrite_tracker(path: Path, records: Sequence[PostRecord]) -> None:
    content = "".join(
        json.dumps(record.to_dict(), ensure_ascii=False) + "\n" for record in records
    )
    atomic_write_text(path, content)


def load_previous_run_state(
    config: AppConfig, logger: logging.Logger
) -> dict[str, Any] | None:
    if not config.run_state_file.exists():
        return None

    try:
        data = json.loads(config.run_state_file.read_text(encoding="utf-8"))
        logger.warning(
            "Recovered unfinished run state from previous execution: %s",
            data,
        )
        return data
    except Exception:
        logger.exception("Could not read previous run state file.")
        return None


def mark_run_state(
    config: AppConfig,
    post: instaloader.Post,
    step: str,
    index: int | None,
    total_posts: int | None,
    **extra: Any,
) -> None:
    payload: dict[str, Any] = {
        "status": "in_progress",
        "step": step,
        "shortcode": post.shortcode,
        "date_utc": str(post.date_utc),
        "post_index": index,
        "total_posts": total_posts,
        "updated_at_utc": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
    }
    payload.update(extra)
    atomic_write_json(config.run_state_file, payload)


def clear_run_state(config: AppConfig) -> None:
    if config.run_state_file.exists():
        config.run_state_file.unlink()


def recover_unfinished_state(
    previous_state: dict[str, Any] | None,
    processed_shortcodes: set[str],
    logger: logging.Logger,
) -> str | None:
    if not previous_state:
        return None

    shortcode = str(previous_state.get("shortcode", "") or "").strip()
    if not shortcode:
        return None

    if shortcode in processed_shortcodes:
        logger.info(
            "Previous unfinished shortcode %s is already in the trackers. Ignoring old run_state.",
            shortcode,
        )
        return None

    partial_folder = str(previous_state.get("final_folder", "") or "").strip()
    if partial_folder:
        partial_path = Path(partial_folder)
        if partial_path.exists():
            logger.warning(
                "Removing partial output folder from interrupted run before retry: %s",
                partial_path,
            )
            safe_rmtree(partial_path, logger)

    workspace = str(previous_state.get("workspace", "") or "").strip()
    if workspace:
        workspace_path = Path(workspace)
        if workspace_path.exists():
            logger.info(
                "Reusing existing workspace from interrupted run for shortcode %s: %s",
                shortcode,
                workspace_path,
            )

    return shortcode


def persist_session_snapshot(
    loader: instaloader.Instaloader,
    config: AppConfig,
    logger: logging.Logger,
) -> None:
    if not config.ig_username or not config.ig_session_file:
        return
    try:
        loader.save_session_to_file(filename=config.ig_session_file)
    except Exception:
        logger.exception("Failed to save Instagram session snapshot to disk.")


def initialize_instaloader(
    config: AppConfig, logger: logging.Logger
) -> instaloader.Instaloader:
    loader = instaloader.Instaloader(
        download_video_thumbnails=True,
        save_metadata=True,
        post_metadata_txt_pattern="",
    )

    if config.ig_username and config.ig_session_file:
        logger.info("Attempting to load Instagram session for %s", config.ig_username)
        try:
            loader.load_session_from_file(
                config.ig_username, filename=config.ig_session_file
            )
            logger.info(
                "Instagram session loaded successfully from %s. Session files usually do not "
                "expire, but expiry cannot be predicted reliably in advance, so this "
                "script relies on resumable state and periodic session snapshots.",
                config.ig_session_file,
            )
            persist_session_snapshot(loader, config, logger)
        except Exception:
            logger.exception(
                "Could not load Instagram session from %s. Run: instaloader --login %s",
                config.ig_session_file,
                config.ig_username,
            )

    return loader


def classify_post(post: instaloader.Post, logger: logging.Logger) -> str:
    if getattr(post, "is_video", False):
        return "video"

    if getattr(post, "typename", "") == "GraphSidecar":
        try:
            nodes = list(post.get_sidecar_nodes())
            has_video = any(getattr(node, "is_video", False) for node in nodes)
            has_image = any(not getattr(node, "is_video", False) for node in nodes)

            if has_video and has_image:
                return "mixed"
            if has_video:
                return "video"
            if has_image:
                return "image"
        except Exception:
            logger.exception(
                "Could not inspect sidecar nodes for post %s", post.shortcode
            )

    return "image"


def list_downloaded_media(
    workspace: Path,
) -> tuple[list[Path], list[Path], list[Path]]:
    files = sorted(path for path in workspace.iterdir() if path.is_file())
    image_files = [
        path
        for path in files
        if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    ]
    video_files = [path for path in files if path.suffix.lower() == ".mp4"]
    return files, image_files, video_files


def download_post_with_retry(
    loader: instaloader.Instaloader,
    post: instaloader.Post,
    workspace: Path,
    config: AppConfig,
    logger: logging.Logger,
    shutdown: GracefulShutdown,
) -> bool:
    for attempt in range(1, config.download_attempts + 1):
        if shutdown.should_stop():
            return False
        try:
            loader.download_post(post, target=str(workspace))
            return True
        except Exception:
            sleep_for = calculate_retry_delay(
                attempt=attempt,
                base=config.retry_base_delay_seconds,
                maximum=config.retry_max_delay_seconds,
            )
            logger.exception(
                "Download failed for %s on attempt %s/%s. Sleeping %.1fs.",
                post.shortcode,
                attempt,
                config.download_attempts,
                sleep_for,
            )
            if attempt < config.download_attempts:
                interrupted = shutdown.sleep(
                    sleep_for, logger, "download retry backoff"
                )
                if interrupted:
                    return False
    return False


def extract_hashtags(caption: str | None) -> str:
    if not caption:
        return ""
    hashtags = re.findall(r"#(\w+)", caption)
    return ", ".join(f"#{tag}" for tag in hashtags)


def make_unique_directory(path: Path) -> Path:
    if not path.exists():
        return path

    counter = 1
    while True:
        candidate = path.parent / f"{path.name}_{counter}"
        if not candidate.exists():
            return candidate
        counter += 1


def route_post_directory(
    config: AppConfig,
    post: instaloader.Post,
    ai_title: str,
    normalized_title: str,
    processed_titles: set[str],
) -> tuple[Path, bool]:
    date_prefix = post.date_utc.strftime("%Y-%m-%d")
    datetime_prefix = post.date_utc.strftime("%Y-%m-%d_%H-%M-%S")

    is_duplicate = False
    if ai_title in {MANUAL_REVIEW, VIDEO_POST}:
        folder_name = f"{date_prefix}_{ai_title}_{post.shortcode}"
        base_path = config.manual_dir / folder_name
    elif normalized_title in processed_titles:
        is_duplicate = True
        folder_name = f"{ai_title}_{datetime_prefix}"
        base_path = config.duplicates_dir / folder_name
    else:
        folder_name = f"{date_prefix}_{ai_title}"
        base_path = config.organized_dir / folder_name

    return make_unique_directory(base_path), is_duplicate


def process_downloaded_files(
    workspace: Path,
    destination: Path,
    logger: logging.Logger,
) -> None:
    metadata_dir = destination / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)

    for source_path in sorted(workspace.iterdir()):
        if not source_path.is_file():
            continue

        if source_path.name.endswith(".json.xz"):
            json_filename = source_path.name[:-3]
            target_path = metadata_dir / json_filename
            try:
                with lzma.open(source_path, "rt", encoding="utf-8") as source_handle:
                    metadata_obj = json.load(source_handle)
                atomic_write_json(target_path, metadata_obj)
                source_path.unlink(missing_ok=True)
            except Exception:
                logger.exception(
                    "Could not parse compressed metadata for %s. Moving original file.",
                    source_path.name,
                )
                shutil.move(str(source_path), str(metadata_dir / source_path.name))
        else:
            shutil.move(str(source_path), str(destination / source_path.name))


def write_post_support_files(
    post: instaloader.Post,
    destination: Path,
    total_followers: int,
    config: AppConfig,
    logger: logging.Logger,
) -> tuple[str, str]:
    caption = post.caption or ""
    hashtags = extract_hashtags(caption)

    likes = post.likes or 0
    comments_count = post.comments or 0
    engagement_rate = (
        ((likes + comments_count) / total_followers * 100.0)
        if total_followers > 0
        else 0.0
    )

    if config.save_hashtags_file and hashtags:
        atomic_write_text(destination / "hashtags.txt", hashtags + "\n")

    if config.save_caption_file:
        atomic_write_text(destination / "caption.txt", (caption or "No caption") + "\n")

    engagement_text = (
        "=== ENGAGEMENT METRICS ===\n"
        f"Likes: {likes}\n"
        f"Comments: {comments_count}\n"
        f"Engagement Rate: {engagement_rate:.2f}%\n"
    )
    atomic_write_text(destination / "engagement.txt", engagement_text)

    notes_lines = [
        "=== POST DETAILS ===",
        f"Date: {post.date_utc.strftime('%Y-%m-%d')}",
        f"Time: {post.date_utc.strftime('%H:%M:%S UTC')}",
        f"Shortcode: {post.shortcode}",
        "",
        "=== CAPTION ===",
        caption if caption else "No caption",
        "",
        "=== COMMENTS ===",
    ]

    if config.fetch_comments:
        try:
            has_any_comment = False
            for comment in post.get_comments():
                has_any_comment = True
                notes_lines.append(f"[{comment.owner.username}]: {comment.text}")
                for answer in comment.answers:
                    notes_lines.append(
                        f"    -> [{answer.owner.username}]: {answer.text}"
                    )
            if not has_any_comment:
                notes_lines.append("(No comments found)")
        except Exception:
            notes_lines.append("(Failed to load comments)")
            logger.exception("Failed to load comments for post %s", post.shortcode)
    else:
        notes_lines.append("(Comment fetching disabled by configuration)")

    atomic_write_text(destination / "notes.txt", "\n".join(notes_lines) + "\n")
    return hashtags, f"{engagement_rate:.2f}%"


def build_post_record(
    post: instaloader.Post,
    ai_title: str,
    normalized_title: str,
    media_type: str,
    hashtags: str,
    engagement: str,
    folder: Path,
    config: AppConfig,
) -> PostRecord:
    return PostRecord(
        shortcode=post.shortcode,
        title=ai_title,
        normalized_title=normalized_title,
        media_type=media_type,
        date=post.date_utc.strftime("%Y-%m-%d"),
        time=post.date_utc.strftime("%H:%M:%S UTC"),
        engagement=engagement,
        hashtags=hashtags,
        timestamp=post.date_utc.timestamp(),
        folder=str(folder.relative_to(config.base_dir)),
    )


def render_text_index(title: str, records: Sequence[PostRecord]) -> str:
    lines = [f"=== {title} ===\n"]
    for record in sorted(records, key=lambda item: item.timestamp):
        tags = f" | {record.hashtags}" if record.hashtags else ""
        folder = f" | {record.folder}" if record.folder else ""
        media = f" | {record.media_type}" if record.media_type else ""
        lines.append(
            f"- {record.title} | {record.date} | {record.time} | "
            f"{record.engagement}{media}{tags}{folder}\n"
        )
    return "".join(lines)


def write_indexes(
    config: AppConfig,
    master_records: Sequence[PostRecord],
    duplicate_records: Sequence[PostRecord],
) -> None:
    atomic_write_text(
        config.master_index_file,
        render_text_index("MASTER POST INDEX", master_records),
    )

    if duplicate_records:
        atomic_write_text(
            config.duplicates_index_file,
            render_text_index("MASTER DUPLICATES INDEX", duplicate_records),
        )
    elif config.duplicates_index_file.exists():
        config.duplicates_index_file.unlink()

    if config.include_json_indexes:
        atomic_write_json(
            config.master_index_file.with_suffix(".json"),
            [
                record.to_dict()
                for record in sorted(master_records, key=lambda item: item.timestamp)
            ],
        )
        atomic_write_json(
            config.duplicates_index_file.with_suffix(".json"),
            [
                record.to_dict()
                for record in sorted(duplicate_records, key=lambda item: item.timestamp)
            ],
        )


def render_ai_analysis_text(payload: dict[str, Any]) -> str:
    if not payload:
        return ""

    parts: list[str] = []

    per_image_analysis = payload.get("per_image_analysis")
    if isinstance(per_image_analysis, list) and per_image_analysis:
        parts.append("=== PER IMAGE ANALYSIS ===")
        for index, item in enumerate(per_image_analysis, start=1):
            parts.append("")
            parts.append(f"Image {index}:")
            parts.append(str(item))

    ocr_summary = payload.get("ocr_summary")
    if ocr_summary:
        parts.append("")
        parts.append("=== OCR SUMMARY ===")
        parts.append(str(ocr_summary))

    dominant_signal = payload.get("dominant_signal")
    if dominant_signal:
        parts.append("")
        parts.append("=== DOMINANT SIGNAL ===")
        parts.append(str(dominant_signal))

    combined_analysis = payload.get("combined_analysis")
    if combined_analysis:
        parts.append("")
        parts.append("=== COMBINED ANALYSIS ===")
        parts.append(str(combined_analysis))

    title = payload.get("title")
    if title:
        parts.append("")
        parts.append("=== FINAL TITLE ===")
        parts.append(str(title))

    return "\n".join(parts).strip()


def save_ai_analysis_files(
    destination: Path,
    ai_result: AITitleResult,
    config: AppConfig,
) -> None:
    if config.save_ai_analysis_text and ai_result.analysis_text:
        atomic_write_text(destination / "ai_analysis.txt", ai_result.analysis_text + "\n")

    if config.save_ai_analysis_json and ai_result.payload:
        atomic_write_json(destination / "ai_analysis.json", ai_result.payload)


def process_post(
    *,
    loader: instaloader.Instaloader,
    post: instaloader.Post,
    index: int | None,
    total_posts: int | None,
    total_followers: int,
    config: AppConfig,
    logger: logging.Logger,
    shutdown_handler: GracefulShutdown,
    title_generator: GeminiTitleGenerator,
    processed_shortcodes: set[str],
    processed_titles: set[str],
    master_records: list[PostRecord],
    duplicate_records: list[PostRecord],
) -> bool:
    if shutdown_handler.should_stop():
        return False

    if post.shortcode in processed_shortcodes:
        logger.info("Skipping %s because it was already processed.", post.shortcode)
        return False

    workspace = create_or_reuse_post_workspace(config, post.shortcode)
    completed_successfully = False

    mark_run_state(
        config,
        post,
        "starting",
        index,
        total_posts,
        workspace=str(workspace),
    )

    try:
        mark_run_state(
            config,
            post,
            "downloading",
            index,
            total_posts,
            workspace=str(workspace),
        )
        download_success = download_post_with_retry(
            loader=loader,
            post=post,
            workspace=workspace,
            config=config,
            logger=logger,
            shutdown=shutdown_handler,
        )
        if not download_success:
            logger.error(
                "Failed to download post %s after %s attempts. Skipping.",
                post.shortcode,
                config.download_attempts,
            )
            return False

        _all_files, image_files, _video_files = list_downloaded_media(workspace)
        media_type = classify_post(post, logger)

        mark_run_state(
            config,
            post,
            "analyzing",
            index,
            total_posts,
            workspace=str(workspace),
            media_type=media_type,
        )

        if media_type in {"image", "mixed"}:
            if image_files:
                logger.info(
                    "Found %s image file(s). Sending up to %s to Gemini.",
                    len(image_files),
                    config.max_ai_images,
                )
                ai_result = title_generator.generate_title(
                    image_paths=image_files,
                    caption=post.caption or "",
                )
            else:
                logger.warning(
                    "Post %s was classified as %s but no image files were found.",
                    post.shortcode,
                    media_type,
                )
                ai_result = AITitleResult(MANUAL_REVIEW, "", {})
        elif media_type == "video":
            logger.info("Pure video post detected. Skipping AI image title generation.")
            ai_result = AITitleResult(VIDEO_POST, "", {})
        else:
            logger.warning(
                "Unknown media classification for %s. Routing to manual review.",
                post.shortcode,
            )
            ai_result = AITitleResult(MANUAL_REVIEW, "", {})

        final_folder, is_duplicate = route_post_directory(
            config=config,
            post=post,
            ai_title=ai_result.title,
            normalized_title=ai_result.normalized_title,
            processed_titles=processed_titles,
        )

        mark_run_state(
            config,
            post,
            "writing_files",
            index,
            total_posts,
            workspace=str(workspace),
            final_folder=str(final_folder),
            media_type=media_type,
            ai_title=ai_result.title,
        )

        final_folder.mkdir(parents=True, exist_ok=True)

        process_downloaded_files(
            workspace=workspace,
            destination=final_folder,
            logger=logger,
        )

        hashtags, engagement = write_post_support_files(
            post=post,
            destination=final_folder,
            total_followers=total_followers,
            config=config,
            logger=logger,
        )

        save_ai_analysis_files(final_folder, ai_result, config)

        record = build_post_record(
            post=post,
            ai_title=ai_result.title,
            normalized_title=ai_result.normalized_title,
            media_type=media_type,
            hashtags=hashtags,
            engagement=engagement,
            folder=final_folder,
            config=config,
        )

        if is_duplicate:
            duplicate_records.append(record)
            append_jsonl(config.duplicates_tracker_file, record.to_dict())
        else:
            master_records.append(record)
            append_jsonl(config.tracker_file, record.to_dict())
            if ai_result.title not in {MANUAL_REVIEW, VIDEO_POST}:
                processed_titles.add(ai_result.normalized_title)

        processed_shortcodes.add(post.shortcode)
        clear_run_state(config)
        completed_successfully = True

        logger.info("Successfully saved post %s to %s", post.shortcode, final_folder)
        return True
    finally:
        if completed_successfully:
            safe_rmtree(workspace, logger)


def main() -> int:
    config: AppConfig | None = None
    logger: logging.Logger | None = None
    master_records: list[PostRecord] = []
    duplicate_records: list[PostRecord] = []
    shutdown_handler = GracefulShutdown()

    try:
        config = AppConfig.from_env()
    except Exception as exc:
        print(f"[!] {exc}")
        return 1

    logger = setup_logging(config)
    logger.info(
        "Starting Instagram organizer for target account: %s", config.target_account
    )
    logger.info("Base directory: %s", config.base_dir)
    logger.info("Local workspace temp base: %s", config.temp_base_dir)
    if config.ig_session_file:
        logger.info("Instagram session file: %s", config.ig_session_file)

    try:
        ensure_directories(config)
        previous_state = load_previous_run_state(config, logger)

        loader = initialize_instaloader(config, logger)
        title_generator = GeminiTitleGenerator(config, logger, shutdown_handler)

        logger.info("Fetching profile: %s", config.target_account)
        profile = instaloader.Profile.from_username(loader.context, config.target_account)

        processed_shortcodes: set[str] = set()
        processed_titles: set[str] = set()

        master_records = load_tracker(
            config.tracker_file,
            processed_shortcodes=processed_shortcodes,
            processed_titles=processed_titles,
            logger=logger,
        )
        duplicate_records = load_tracker(
            config.duplicates_tracker_file,
            processed_shortcodes=processed_shortcodes,
            processed_titles=None,
            logger=logger,
        )

        priority_shortcode = recover_unfinished_state(
            previous_state=previous_state,
            processed_shortcodes=processed_shortcodes,
            logger=logger,
        )

        total_posts = profile.mediacount
        total_followers = profile.followers
        processed_since_session_persist = 0

        logger.info("--- TARGET IDENTIFIED ---")
        logger.info("Total Posts: %s", total_posts)
        logger.info("Followers: %s", total_followers)

        if priority_shortcode and not shutdown_handler.should_stop():
            try:
                logger.warning(
                    "Retrying unfinished shortcode first before normal feed scan: %s",
                    priority_shortcode,
                )
                priority_post = instaloader.Post.from_shortcode(
                    loader.context, priority_shortcode
                )
                processed = process_post(
                    loader=loader,
                    post=priority_post,
                    index=None,
                    total_posts=total_posts,
                    total_followers=total_followers,
                    config=config,
                    logger=logger,
                    shutdown_handler=shutdown_handler,
                    title_generator=title_generator,
                    processed_shortcodes=processed_shortcodes,
                    processed_titles=processed_titles,
                    master_records=master_records,
                    duplicate_records=duplicate_records,
                )
                if processed:
                    processed_since_session_persist += 1
            except Exception:
                logger.exception(
                    "Failed while retrying unfinished shortcode %s. Continuing with normal scan.",
                    priority_shortcode,
                )

        for index, post in enumerate(profile.get_posts(), start=1):
            if shutdown_handler.should_stop():
                logger.warning("Graceful shutdown triggered. Exiting post loop.")
                break

            logger.info("--- Processing Post %s of %s ---", index, total_posts)
            logger.info("Date: %s | ID: %s", post.date_utc, post.shortcode)

            processed = process_post(
                loader=loader,
                post=post,
                index=index,
                total_posts=total_posts,
                total_followers=total_followers,
                config=config,
                logger=logger,
                shutdown_handler=shutdown_handler,
                title_generator=title_generator,
                processed_shortcodes=processed_shortcodes,
                processed_titles=processed_titles,
                master_records=master_records,
                duplicate_records=duplicate_records,
            )

            if processed:
                processed_since_session_persist += 1
                if (
                    config.persist_session_every_posts > 0
                    and processed_since_session_persist
                    >= config.persist_session_every_posts
                ):
                    persist_session_snapshot(loader, config, logger)
                    processed_since_session_persist = 0

                if config.instagram_pause_seconds > 0:
                    logger.info(
                        "Sleeping for %.1f seconds to reduce Instagram request pressure.",
                        config.instagram_pause_seconds,
                    )
                    shutdown_handler.sleep(
                        config.instagram_pause_seconds,
                        logger,
                        "Instagram pacing pause",
                    )

    except Exception:
        logger.exception("Fatal error while processing Instagram posts.")
        return 1
    finally:
        try:
            if config is not None and logger is not None:
                rewrite_tracker(config.tracker_file, master_records)
                rewrite_tracker(config.duplicates_tracker_file, duplicate_records)
                write_indexes(config, master_records, duplicate_records)
                logger.info("Indexes written. Safe to exit.")
        except Exception:
            if logger is not None:
                logger.exception("Failed while writing tracker or index files.")
            else:
                print("[!] Failed while writing tracker or index files.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
