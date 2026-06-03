import os
import re
import csv
from datetime import datetime


SUPPORTED_EXTENSIONS = ["csv", "qbo", "qfx", "ofx",
    # "csv","xlsx","xls","qbo","qfx","ofx","pdf","jpg","jpeg","png",
]


def parse_bank_file(file_path: str):
    """
    خروجی استاندارد برای همه فرمت‌ها:
    {
        "ok": True/False,
        "detected_format": "csv/pdf/...",
        "rows": [...],
        "warnings": [...],
        "error": None
    }
    """

    file_path = (file_path or "").strip()

    if not file_path:
        return _error("مسیر فایل خالی است.")

    if not os.path.exists(file_path):
        return _error(f"فایل پیدا نشد: {file_path}")

    ext = _get_ext(file_path)

    print("[BANK PARSER] file_path:", file_path, flush=True)
    print("[BANK PARSER] ext:", ext, flush=True)
    print("[BANK PARSER] exists:", os.path.exists(file_path), flush=True)
    print("[BANK PARSER] size:", os.path.getsize(file_path) if os.path.exists(file_path) else 0, flush=True)


    if ext not in SUPPORTED_EXTENSIONS:
        return _error(f"فرمت فایل پشتیبانی نمی‌شود: {ext}")

    try:
        if ext == "csv":
            return parse_csv_file(file_path)

        if ext in ("xlsx", "xls"):
            return parse_excel_file(file_path)

        if ext in ("qbo", "qfx", "ofx"):
            return parse_ofx_file(file_path)

        if ext == "pdf":
            return parse_pdf_file(file_path)

        if ext in ("jpg", "jpeg", "png"):
            return parse_image_file(file_path)

        return _error(f"Parser برای {ext} آماده نیست.")

    except Exception as ex:
        return _error(f"خطا در خواندن فایل: {ex}", detected_format=ext)


# ---------------------------------------------------------
# Common helpers
# ---------------------------------------------------------

def _error(message, detected_format=None):
    return {
        "ok": False,
        "detected_format": detected_format,
        "rows": [],
        "warnings": [],
        "error": message,
    }


def _success(detected_format, rows, warnings=None):
    return {
        "ok": True,
        "detected_format": detected_format,
        "rows": rows or [],
        "warnings": warnings or [],
        "error": None,
    }


def _get_ext(file_path):
    name = os.path.basename(file_path or "")
    if "." not in name:
        return ""
    return name.rsplit(".", 1)[-1].lower().strip()


def _clean_text(value):
    if value is None:
        return ""

    value = str(value)
    value = value.replace("\u200f", "").replace("\u200e", "")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _parse_amount(value):
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    # نمونه‌ها:
    # $1,234.56
    # -45.20
    # (45.20)
    # 45.20 CR
    # 45.20 DR

    negative = False

    if "(" in text and ")" in text:
        negative = True

    upper = text.upper()
    if "DR" in upper:
        negative = True
    if "DEBIT" in upper:
        negative = True

    text = text.replace(",", "")
    text = text.replace("$", "")
    text = text.replace("CAD", "")
    text = text.replace("USD", "")
    text = text.replace("CR", "")
    text = text.replace("DR", "")
    text = text.replace("DEBIT", "")
    text = text.replace("CREDIT", "")
    text = text.replace("(", "")
    text = text.replace(")", "")
    text = text.strip()

    match = re.search(r"-?\d+(\.\d+)?", text)
    if not match:
        return None

    amount = float(match.group(0))

    if negative and amount > 0:
        amount = -amount

    return round(amount, 2)


def _parse_date(value):
    if value is None:
        return None

    text = _clean_text(value)

    if not text:
        return None

    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%m-%d-%Y",
        "%d-%m-%Y",
        "%b %d %Y",
        "%b %d, %Y",
        "%d %b %Y",
        "%Y%m%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except Exception:
            pass

    # پیدا کردن تاریخ داخل متن
    patterns = [
        r"\d{4}-\d{2}-\d{2}",
        r"\d{4}/\d{2}/\d{2}",
        r"\d{1,2}/\d{1,2}/\d{4}",
        r"\d{1,2}-\d{1,2}-\d{4}",
    ]

    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            return _parse_date(m.group(0))

    return None


def _detect_transaction_type(amount, description=""):
    desc = (description or "").lower()

    if "transfer" in desc or "e-transfer" in desc or "etransfer" in desc:
        return "transfer"

    if "refund" in desc or "return" in desc or "reversal" in desc:
        return "refund"

    if amount is None:
        return "unknown"

    if amount < 0:
        return "expense"

    if amount > 0:
        return "income"

    return "unknown"


def _standard_row(
    row_index,
    bank_date=None,
    description=None,
    amount=None,
    raw_text=None,
    confidence_score=0.80,
):
    description = _clean_text(description)
    raw_text = raw_text if raw_text is not None else description

    tx_type = _detect_transaction_type(amount, description)

    match_status = "new"
    if not bank_date or amount is None:
        match_status = "needs_review"

    return {
        "row_index": row_index,
        "bank_date": bank_date,
        "bank_description": description or "Bank transaction",
        "raw_text": raw_text,
        "amount": amount,
        "currency": "CAD",
        "transaction_type": tx_type,
        "match_status": match_status,
        "confidence_score": confidence_score,
    }


def _find_column(columns, keywords):
    """
    columns: list of column names
    keywords: possible names
    """
    normalized = {
        str(c).strip().lower(): c
        for c in columns
        if c is not None
    }

    for key in keywords:
        key = key.lower()
        for col_lower, original in normalized.items():
            if key == col_lower or key in col_lower:
                return original

    return None


# ---------------------------------------------------------
# CSV
# ---------------------------------------------------------

def parse_csv_file(file_path):
    rows = []
    warnings = []

    encodings = ["utf-8-sig", "utf-8", "cp1252", "latin1"]
    last_error = None

    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding, newline="") as f:
                sample = f.read(4096)
                f.seek(0)

                try:
                    dialect = csv.Sniffer().sniff(sample)
                except Exception:
                    dialect = csv.excel

                reader = csv.reader(f, dialect=dialect)
                raw_rows = list(reader)

            if not raw_rows:
                return _error("CSV خالی است.", detected_format="csv")

            header_index = _find_real_csv_header_index(raw_rows)

            if header_index is None:
                return _error(
                    "ردیف عنوان ستون‌ها در CSV پیدا نشد.",
                    detected_format="csv",
                )

            header = [
                _clean_text(h) or f"col_{i}"
                for i, h in enumerate(raw_rows[header_index])
            ]

            records = []

            for raw_index, raw_row in enumerate(raw_rows[header_index + 1:], start=header_index + 2):
                if not raw_row:
                    continue

                if all(not _clean_text(x) for x in raw_row):
                    continue

                item = {}

                for i, value in enumerate(raw_row):
                    key = header[i] if i < len(header) else f"extra_{i}"
                    item[key] = value

                item["_source_row_number"] = raw_index
                records.append(item)

            parsed = _parse_table_dict_rows(records)

            print("[BANK PARSER] csv header_index:", header_index, flush=True)
            print("[BANK PARSER] csv header:", header, flush=True)
            print("[BANK PARSER] csv parsed rows:", len(parsed), flush=True)

            rows.extend(parsed)
            return _success("csv", rows, warnings)

        except Exception as ex:
            last_error = ex

    return _error(f"CSV خوانده نشد: {last_error}", detected_format="csv")


def _find_real_csv_header_index(raw_rows):
    """
    بعضی خروجی‌های بانک مثل BMO چند ردیف توضیح قبل از header دارند.
    این تابع ردیفی را پیدا می‌کند که واقعاً شامل ستون‌های تراکنش است.
    """

    header_keywords = [
        "date",
        "posted",
        "transaction",
        "amount",
        "description",
        "debit",
        "credit",
        "withdrawal",
        "deposit",
        "memo",
        "details",
    ]

    best_index = None
    best_score = 0

    for index, row in enumerate(raw_rows):
        cleaned_cells = [
            _clean_text(cell).lower()
            for cell in row
            if _clean_text(cell)
        ]

        if not cleaned_cells:
            continue

        score = 0

        for cell in cleaned_cells:
            for keyword in header_keywords:
                if keyword in cell:
                    score += 1

        # حداقل باید چند ستون مرتبط پیدا شود
        if score > best_score:
            best_score = score
            best_index = index

    if best_score >= 2:
        return best_index

    return None


# ---------------------------------------------------------
# Excel
# ---------------------------------------------------------

def parse_excel_file(file_path):
    try:
        import pandas as pd
    except Exception:
        return _error("کتابخانه pandas/openpyxl نصب نیست.", detected_format="excel")

    try:
        df = pd.read_excel(file_path)
        records = df.fillna("").to_dict(orient="records")
        rows = _parse_table_dict_rows(records)
        return _success("excel", rows)

    except Exception as ex:
        return _error(f"Excel خوانده نشد: {ex}", detected_format="excel")


def _parse_table_dict_rows(records):
    print("[BANK PARSER] records count:", len(records or []), flush=True)

    if records:
        print("[BANK PARSER] first record:", records[0], flush=True)
        print("[BANK PARSER] columns:", list(records[0].keys()), flush=True)
        
    if not records:
        return []

    columns = list(records[0].keys())

    date_col = _find_column(
        columns,
        [
            "date",
            "transaction date",
            "posted date",
            "posting date",
            "effective date",
            "activity date",
            "process date",
            "تاریخ",
        ],
    )

    desc_col = _find_column(
        columns,
        [
            "description",
            "details",
            "transaction",
            "transaction description",
            "merchant",
            "memo",
            "payee",
            "name",
            "particulars",
            "شرح",
            "توضیح",
        ],
    )

    amount_col = _find_column(
        columns,
        [
            "amount",
            "transaction amount",
            "cad$",
            "cad",
            "مبلغ",
        ],
    )

    debit_col = _find_column(
        columns,
        [
            "debit",
            "withdrawal",
            "withdrawals",
            "money out",
            "paid out",
            "برداشت",
        ],
    )

    credit_col = _find_column(
        columns,
        [
            "credit",
            "deposit",
            "deposits",
            "money in",
            "paid in",
            "واریز",
        ],
    )

    rows = []

    for i, item in enumerate(records, start=1):
        bank_date = _parse_date(item.get(date_col)) if date_col else None
        description = _clean_text(item.get(desc_col)) if desc_col else ""

        amount = None

        if amount_col:
            amount = _parse_amount(item.get(amount_col))

        if amount is None and (debit_col or credit_col):
            debit = _parse_amount(item.get(debit_col)) if debit_col else None
            credit = _parse_amount(item.get(credit_col)) if credit_col else None

            if debit is not None and abs(debit) > 0:
                amount = -abs(debit)
            elif credit is not None and abs(credit) > 0:
                amount = abs(credit)

        raw_text = " | ".join([
            f"{k}: {v}"
            for k, v in item.items()
            if _clean_text(v)
        ])

        # اگر ردیف کاملاً خالی بود skip
        if not bank_date and amount is None and not description:
            continue

        confidence = 0.95 if bank_date and amount is not None else 0.55

        rows.append(
            _standard_row(
                row_index=i,
                bank_date=bank_date,
                description=description,
                amount=amount,
                raw_text=raw_text,
                confidence_score=confidence,
            )
        )
    print("[BANK PARSER] detected date_col:", date_col, flush=True)
    print("[BANK PARSER] detected desc_col:", desc_col, flush=True)
    print("[BANK PARSER] detected amount_col:", amount_col, flush=True)
    print("[BANK PARSER] detected debit_col:", debit_col, flush=True)
    print("[BANK PARSER] detected credit_col:", credit_col, flush=True)

    return rows


# ---------------------------------------------------------
# OFX / QBO / QFX
# ---------------------------------------------------------

def parse_ofx_file(file_path):
    try:
        from ofxparse import OfxParser
    except Exception:
        return parse_ofx_file_basic(file_path)

    try:
        with open(file_path, "rb") as f:
            ofx = OfxParser.parse(f)

        result_rows = []
        index = 1

        accounts = []

        if getattr(ofx, "accounts", None):
            accounts = ofx.accounts

        for account in accounts:
            statement = getattr(account, "statement", None)
            if not statement:
                continue

            transactions = getattr(statement, "transactions", []) or []

            for tx in transactions:
                amount = float(getattr(tx, "amount", 0) or 0)

                tx_date = getattr(tx, "date", None)
                bank_date = tx_date.date().isoformat() if tx_date else None

                description = (
                    getattr(tx, "payee", None)
                    or getattr(tx, "memo", None)
                    or getattr(tx, "id", None)
                    or "Bank transaction"
                )

                raw_text = str(tx)

                result_rows.append(
                    _standard_row(
                        row_index=index,
                        bank_date=bank_date,
                        description=description,
                        amount=round(amount, 2),
                        raw_text=raw_text,
                        confidence_score=0.98,
                    )
                )
                index += 1

        if result_rows:
            return _success("ofx", result_rows)

        return _error("هیچ تراکنشی در فایل OFX/QBO/QFX پیدا نشد.", detected_format="ofx")

    except Exception:
        return parse_ofx_file_basic(file_path)

def parse_ofx_file_basic(file_path):
    ext = _get_ext(file_path) or "ofx"

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except Exception as ex:
        return _error(f"OFX/QBO/QFX خوانده نشد: {ex}", detected_format=ext)

    blocks = re.findall(
        r"<STMTTRN>(.*?)(?=<STMTTRN>|</BANKTRANLIST>|</CREDITCARDMSGSRSV1>|$)",
        text,
        re.S | re.I
    )

    rows = []

    for i, block in enumerate(blocks, start=1):
        trn_date = _tag_value(block, "DTPOSTED")
        amount_text = _tag_value(block, "TRNAMT")
        name = _tag_value(block, "NAME")
        memo = _tag_value(block, "MEMO")

        bank_date = None
        if trn_date:
            bank_date = _parse_date(trn_date[:8])

        amount = _parse_amount(amount_text)
        description = name or memo or "Bank transaction"

        rows.append(
            _standard_row(
                row_index=i,
                bank_date=bank_date,
                description=description,
                amount=amount,
                raw_text=block,
                confidence_score=0.90 if bank_date and amount is not None else 0.60,
            )
        )

    if not rows:
        return _error("در فایل OFX/QBO/QFX تراکنشی پیدا نشد.", detected_format=ext)

    warnings = [
        "این فایل با parser ساده خوانده شد، نه ofxparse. لطفاً تراکنش‌ها را قبل از ثبت بررسی کنید."
    ]

    return _success(ext, rows, warnings)



def _tag_value(text, tag):
    pattern = rf"<{tag}>([^\r\n<]+)"
    m = re.search(pattern, text, re.I)
    if not m:
        return ""
    return _clean_text(m.group(1))


# ---------------------------------------------------------
# PDF
# ---------------------------------------------------------

def parse_pdf_file(file_path):
    warnings = []

    # اول تلاش با pdfplumber برای PDF متنی/جدولی
    try:
        import pdfplumber

        all_rows = []

        with pdfplumber.open(file_path) as pdf:
            for page_index, page in enumerate(pdf.pages, start=1):
                tables = page.extract_tables() or []

                for table in tables:
                    table_rows = _parse_pdf_table(table)
                    all_rows.extend(table_rows)

        if all_rows:
            return _success("pdf", all_rows, warnings)

        warnings.append("جدول مشخصی در PDF پیدا نشد. تلاش با متن خام انجام شد.")

    except Exception as ex:
        warnings.append(f"pdfplumber موفق نبود: {ex}")

    # تلاش دوم: متن خام PDF
    try:
        import fitz

        doc = fitz.open(file_path)
        text_parts = []

        for page in doc:
            text_parts.append(page.get_text())

        text = "\n".join(text_parts)
        rows = parse_statement_text_lines(text)

        if rows:
            return _success("pdf", rows, warnings)

        warnings.append("از متن PDF هم تراکنش مشخصی پیدا نشد.")

    except Exception as ex:
        warnings.append(f"PyMuPDF موفق نبود: {ex}")

    # تلاش سوم: PDF اسکن‌شده → تبدیل به تصویر → OCR
    try:
        import fitz
        from PIL import Image
        import pytesseract
        import tempfile

        doc = fitz.open(file_path)
        ocr_texts = []

        for page_index, page in enumerate(doc, start=1):
            pix = page.get_pixmap(dpi=200)

            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = tmp.name
                pix.save(tmp_path)

            img = Image.open(tmp_path)
            text = pytesseract.image_to_string(img, lang="eng")
            ocr_texts.append(text)

            try:
                os.remove(tmp_path)
            except Exception:
                pass

        rows = parse_statement_text_lines("\n".join(ocr_texts))

        if rows:
            warnings.append("PDF با OCR خوانده شد؛ لطفاً ردیف‌ها را بررسی کنید.")
            return _success("pdf_ocr", rows, warnings)

    except Exception as ex:
        warnings.append(f"OCR برای PDF موفق نبود: {ex}")

    return {
        "ok": False,
        "detected_format": "pdf",
        "rows": [],
        "warnings": warnings,
        "error": "PDF خوانده شد اما تراکنش قابل اطمینان استخراج نشد.",
    }


def _parse_pdf_table(table):
    if not table:
        return []

    # فرض: ردیف اول header است
    header = table[0]
    data_rows = table[1:]

    cleaned_header = [
        _clean_text(h) or f"col_{i}"
        for i, h in enumerate(header)
    ]

    records = []

    for row in data_rows:
        if not row:
            continue

        item = {}

        for i, value in enumerate(row):
            key = cleaned_header[i] if i < len(cleaned_header) else f"col_{i}"
            item[key] = value

        records.append(item)

    return _parse_table_dict_rows(records)


# ---------------------------------------------------------
# Image OCR
# ---------------------------------------------------------

def parse_image_file(file_path):
    try:
        from PIL import Image
        import pytesseract
    except Exception:
        return _error("برای خواندن تصویر، pillow و pytesseract باید نصب باشند.", detected_format="image")

    try:
        img = Image.open(file_path)

        # فعلاً انگلیسی؛ برای فارسی اگر tesseract فارسی نصب بود می‌شود eng+fas گذاشت.
        text = pytesseract.image_to_string(img, lang="eng")

        rows = parse_statement_text_lines(text)

        warnings = [
            "تصویر با OCR خوانده شد. لطفاً تاریخ و مبلغ‌ها را با دقت بررسی کنید."
        ]

        if rows:
            return _success("image_ocr", rows, warnings)

        return {
            "ok": False,
            "detected_format": "image_ocr",
            "rows": [],
            "warnings": warnings,
            "error": "از تصویر تراکنش قابل اطمینان استخراج نشد.",
        }

    except Exception as ex:
        return _error(f"تصویر خوانده نشد: {ex}", detected_format="image")


# ---------------------------------------------------------
# Text-line parser for PDF/OCR
# ---------------------------------------------------------

def parse_statement_text_lines(text):
    text = text or ""
    lines = [
        _clean_text(line)
        for line in text.splitlines()
        if _clean_text(line)
    ]

    rows = []
    index = 1

    for line in lines:
        date_value = _parse_date(line)

        if not date_value:
            continue

        amounts = re.findall(r"[-(]?\$?\d{1,3}(?:,\d{3})*(?:\.\d{2})\)?|\$?\d+\.\d{2}", line)

        if not amounts:
            continue

        # معمولاً آخرین عدد پولی در خط مبلغ تراکنش است
        amount = _parse_amount(amounts[-1])

        description = line

        # حذف تاریخ و مبلغ از description برای تمیزی
        description = description.replace(amounts[-1], "")
        description = re.sub(r"\d{4}-\d{2}-\d{2}", "", description)
        description = re.sub(r"\d{1,2}/\d{1,2}/\d{4}", "", description)
        description = re.sub(r"\s+", " ", description).strip()

        rows.append(
            _standard_row(
                row_index=index,
                bank_date=date_value,
                description=description or "Bank transaction",
                amount=amount,
                raw_text=line,
                confidence_score=0.55,
            )
        )

        index += 1

    return rows