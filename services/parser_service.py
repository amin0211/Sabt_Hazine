import re
import spacy
from quantulum3 import parser as qparser
from word2number import w2n
from services.openai_service import parse_expense_with_openai

nlp = spacy.load("en_core_web_sm")


def extract_quantity(doc):
    quantity = None
    unit = None

    for i, token in enumerate(doc):
        # عدد مثل 2
        if token.like_num:
            try:
                quantity = int(token.text)
            except:
                try:
                    quantity = w2n.word_to_num(token.text)
                except:
                    continue

            # کلمه بعدی → unit
            if i + 1 < len(doc):
                unit = doc[i + 1].text

            break

    return quantity, unit


def extract_money(text):
    price = None
    currency = None

    quants = qparser.parse(text)

    for q in quants:
        if q.unit.entity.name == "currency":
            price = q.value
            currency = q.unit.name
            break

    return price, currency


def extract_title(doc):
    nouns = []

    for token in doc:
        if token.pos_ == "NOUN" and token.text.lower() not in ["cup", "cups"]:
            nouns.append(token.text)

    if nouns:
        return " ".join(nouns)

    return None

def parse_expense_english(text):
    doc = nlp(text)

    quantity, unit = extract_quantity(doc)
    price, currency = extract_money(text)
    title = extract_title(doc)

    return {
        "title": title,
        "quantity": quantity,
        "unit": unit,
        "price": price,
        "currency": currency
    }

def parse_expense(text):
    data = parse_expense_english(text)
    if data["price"] is not None and data["title"] is not None:
        return data

    return parse_expense_with_openai(text)