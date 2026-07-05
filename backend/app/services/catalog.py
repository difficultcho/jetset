from app.models.catalog import Spu


def _first_image(spu: Spu, color_index: int | None = None) -> str | None:
    for img in spu.images:
        if color_index is None or img.color_index == color_index:
            return img.url
    return spu.images[0].url if spu.images else None


def spu_to_list_item(spu: Spu) -> dict:
    colors: dict[int, str] = {}
    for sku in spu.skus:
        colors.setdefault(sku.color_index, sku.color_hex)
    return {
        "id": spu.id,
        "name": spu.name,
        "en_model": spu.en_model,
        "price": spu.price,
        "badge": spu.badge,
        "image": _first_image(spu),
        "color_hexes": [colors[i] for i in sorted(colors)],
    }


def spu_to_detail(spu: Spu) -> dict:
    colors: dict[int, dict] = {}
    sizes: list[str] = []
    for sku in sorted(spu.skus, key=lambda s: s.id):
        if sku.color_index not in colors:
            colors[sku.color_index] = {
                "index": sku.color_index,
                "name": sku.color_name,
                "hex": sku.color_hex,
                "image": _first_image(spu, sku.color_index),
            }
        if sku.size not in sizes:
            sizes.append(sku.size)
    return {
        "id": spu.id,
        "name": spu.name,
        "en_model": spu.en_model,
        "brief": spu.brief,
        "detail": spu.detail,
        "badge": spu.badge,
        "price": spu.price,
        "colors": [colors[i] for i in sorted(colors)],
        "sizes": sizes,
        "skus": [
            {"id": s.id, "color_index": s.color_index, "size": s.size,
             "price": s.price, "stock": s.stock}
            for s in spu.skus if s.status == 1
        ],
    }
