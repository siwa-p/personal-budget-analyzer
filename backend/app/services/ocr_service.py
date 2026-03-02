import io
import re

from PIL import Image
from transformers import AutoProcessor, VisionEncoderDecoderConfig, VisionEncoderDecoderModel

from app.core.logger_init import setup_logging

logger = setup_logging()

MODEL_ID = "naver-clova-ix/donut-base-finetuned-cord-v2"
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB

_processor: AutoProcessor | None = None
_model: VisionEncoderDecoderModel | None = None


def _load_model() -> tuple[AutoProcessor, VisionEncoderDecoderModel]:
    global _processor, _model
    if _processor is None:
        _processor = AutoProcessor.from_pretrained(MODEL_ID, use_fast=False)
        _config = VisionEncoderDecoderConfig.from_pretrained(MODEL_ID)
        _config.decoder.tie_word_embeddings = False
        _model = VisionEncoderDecoderModel.from_pretrained(MODEL_ID, config=_config)
        _model.eval()
    return _processor, _model


def scan_receipt(image_bytes: bytes) -> dict:
    processor, model = _load_model()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    task_prompt = "<s_cord-v2>"
    decoder_input_ids = processor.tokenizer(
        task_prompt, add_special_tokens=False, return_tensors="pt"
    ).input_ids
    pixel_values = processor(image, return_tensors="pt").pixel_values

    outputs = model.generate(
        pixel_values,
        decoder_input_ids=decoder_input_ids,
        max_length=model.decoder.config.max_position_embeddings,
        pad_token_id=processor.tokenizer.pad_token_id,
        eos_token_id=processor.tokenizer.eos_token_id,
        use_cache=True,
        bad_words_ids=[[processor.tokenizer.unk_token_id]],
        return_dict_in_generate=True,
    )

    sequence = processor.batch_decode(outputs.sequences)[0]
    sequence = sequence.replace(processor.tokenizer.eos_token, "")
    sequence = sequence.replace(processor.tokenizer.pad_token, "")
    sequence = re.sub(r"<.*?>", "", sequence, count=1).strip()

    cord = processor.token2json(sequence)
    logger.info("OCR CORD: %s", cord)
    result = _parse_cord(cord)
    logger.info(
        "OCR parsed: amount=%s subtotal=%s tax=%s total_validated=%s dates=%s",
        result["amount"], result["subtotal"], result["tax"], result["total_validated"], result["dates"],
    )
    return result

# Matches M/D/YYYY, MM/DD/YYYY, YYYY-MM-DD
_DATE_RE = re.compile(r"\b(\d{1,4}[-/]\d{1,2}[-/]\d{2,4})\b")


def _extract_dates(cord) -> list[str]:
    dates: list[str] = []
    for v in (cord.get("total") or {}).values():
        if isinstance(v, str):
            dates.extend(_DATE_RE.findall(v))
    for item in (cord.get("menu") or []):
        if isinstance(item, dict):
            for v in item.values():
                if isinstance(v, str):
                    dates.extend(_DATE_RE.findall(v))
    return list(dict.fromkeys(dates))  # deduplicate, preserve order


def _parse_cord(cord) -> dict:
    if isinstance(cord, list):
        cord = next(
            (c for c in cord if isinstance(c, dict) and ("menu" in c or "sub_total" in c)),
            cord[0] if cord else {},
        )
    total_node = cord.get("total") or {}
    sub_total_node = cord.get("sub_total") or {}
    total = _parse_amount(total_node.get("total_price", ""))
    subtotal = _parse_amount(sub_total_node.get("subtotal_price", ""))
    tax = _parse_amount(sub_total_node.get("tax_price", ""))
    # Some receipts (e.g. Walmart) put the grand total in cord['price'] instead of cord['total']['total_price']
    if total is None:
        total = _parse_amount(cord.get("price", ""))
    if total is None and subtotal is not None:
        total = round(subtotal + (tax or 0.0), 2)
    total_validated: bool | None = None
    if total is not None and subtotal is not None and tax is not None:
        total_validated = abs(round(subtotal + tax, 2) - total) <= 0.01

    dates = _extract_dates(cord)

    return {
        "amount": total,
        "tax": tax,
        "subtotal": subtotal,
        "total_validated": total_validated,
        "dates": dates,
        "raw_cord": cord,
    }


def _parse_amount(s: str) -> float | None:
    cleaned = re.sub(r"[^\d.]", "", s)
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None

