from services.supabase_service import create_hazine, update_hazine_embedding, update_hazine, update_hazine_embedding
from services.openai_service import get_embedding

def update_hazine_with_embedding(category_id, title, id_parent=None, is_active=True):
    embedding_text = title

    updated = update_hazine(
        category_id=category_id,
        title=title,
        id_parent=id_parent,
        embedding_text=embedding_text,
        is_active=is_active
    )

    if not updated:
        return None

    embedding_vector = get_embedding(embedding_text)

    if embedding_vector:
        update_hazine_embedding(category_id, embedding_vector)

    return updated

def create_hazine_with_embedding(title, id_parent=None):
    # 1. متن نماینده category
    embedding_text = title

    # 2. ساخت category در DB
    new_cat = create_hazine(
        title=title,
        id_parent=id_parent,
        embedding_text=embedding_text
    )

    if not new_cat:
        return None

    # 3. گرفتن id
    category_id = new_cat["id"]

    # 4. ساخت embedding
    embedding_vector = get_embedding(embedding_text)

    # 5. ذخیره embedding در DB
    if embedding_vector:
        update_hazine_embedding(category_id, embedding_vector)

    return new_cat