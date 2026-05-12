import openpyxl
from pathlib import Path
from app.models.product import Product

PRODUCT_DIR = Path("E:/VIBE/beicaoji/beicaoji-产品目录")
FILE_MAP = {"biscuit": "biscuit.xlsx", "bread": "bread.xlsx", "tea": "tea.xlsx", "toy": "toy.xlsx"}


def import_all(session):
    count = 0
    for category, filename in FILE_MAP.items():
        count += import_sheet(session, PRODUCT_DIR / filename, category)
    session.commit()
    return count


def import_sheet(session, filepath, category):
    wb = openpyxl.load_workbook(filepath)
    ws = wb[wb.sheetnames[0]]
    count = 0
    for row in list(ws.iter_rows(min_row=2, values_only=True)):
        if not row[0]:
            continue
        product = Product(
            sku_id=str(row[0]).strip(),
            category=category,
            feature_tag=str(row[1] or "").strip(),
            name=str(row[2] or "").strip(),
            ingredients=str(row[3] or "").strip(),
            scene_tags=str(row[4] or "").strip(),
            sales_script=str(row[5] or "").strip(),
            contraindication_tags=str(row[6] or "").strip(),
        )
        session.add(product)
        count += 1
    return count