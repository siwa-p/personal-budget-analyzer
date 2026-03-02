import io
import json
import re

from PIL import Image
from transformers import AutoProcessor, VisionEncoderDecoderModel

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
        _model = VisionEncoderDecoderModel.from_pretrained(MODEL_ID)
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
    logger.info("OCR CORD JSON: %s", json.dumps(cord, ensure_ascii=False))
    return _parse_cord(cord)


def _parse_cord(cord) -> dict:
    # token2json can return a list when the sequence has malformed/extra content
    if isinstance(cord, list):
        cord = next(
            (c for c in cord if isinstance(c, dict) and ("menu" in c or "total" in c)),
            cord[0] if cord else {},
        )

    # Try standard CORD total_price, fall back to top-level price
    total_node = cord.get("total", {})
    total_str = total_node.get("total_price", "") if isinstance(total_node, dict) else ""
    if not total_str:
        top_price = cord.get("price", "")
        total_str = top_price if isinstance(top_price, str) else ""
    amount = _parse_amount(total_str)

    items = cord.get("menu", [])
    if not isinstance(items, list):
        items = []
    # nm can be str, dict, or list depending on parse quality — keep only clean strings
    names = [
        i["nm"] for i in items
        if isinstance(i, dict) and isinstance(i.get("nm"), str) and i["nm"].strip()
    ]
    description = ", ".join(names) or None

    return {
        "amount": amount,
        "description": description,
        "raw_cord": cord,
    }


def _parse_amount(s: str) -> float | None:
    cleaned = re.sub(r"[^\d.]", "", s)
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None