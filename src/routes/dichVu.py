
from decimal import Decimal
from functools import wraps

from flask import jsonify, render_template
from sqlalchemy.exc import SQLAlchemyError

from src import app, db
from src.models.models import Category, DichVu, VaiTro
from src.routes.datLich import (
    BookingError, api_error, current_account, positive_id, read_json,
)

MAX_GIA = Decimal(10) ** 12 
REQUIRED_FIELDS = {"name", "gia", "thoi_luong", "category_id"}


def service_errors(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        try:
            return view(*args, **kwargs)
        except BookingError as error:
            db.session.rollback()
            return api_error(error.code, error.message, error.status)
        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception("Lỗi cơ sở dữ liệu khi lưu dịch vụ")
            return api_error("DATABASE_ERROR", "Không thể lưu thay đổi dịch vụ.", 500)
    return wrapped


def dich_vu_to_dict(dich_vu):
    return {
        "id": dich_vu.id,
        "name": dich_vu.name,
        "gia": str(dich_vu.gia) if dich_vu.gia is not None else None,
        "thoi_luong": dich_vu.thoi_luong,
        "category_id": dich_vu.category_id,
        "description": dich_vu.description,
    }


def dich_vu_hien_thi():
    return (db.select(DichVu).join(DichVu.category)
            .where(DichVu.dang_hoat_dong.is_(True), Category.dang_hoat_dong.is_(True)))


def parse_name(raw):
    if not isinstance(raw, str) or not 1 <= len(raw.strip()) <= 100:
        raise BookingError("INVALID_NAME", "Tên dịch vụ phải dài 1–100 ký tự.")
    return raw.strip()


def parse_gia(raw):
    is_digits = isinstance(raw, str) and raw.isascii() and raw.isdigit()
    if not (type(raw) is int or is_digits) or not 0 < Decimal(raw) < MAX_GIA:
        raise BookingError("INVALID_PRICE", "Giá phải là số nguyên đồng dương, tối đa 12 chữ số.")
    return Decimal(raw)


def parse_thoi_luong(raw):
    if type(raw) is not int or not 15 <= raw <= 120:
        raise BookingError("INVALID_DURATION", "Thời lượng phải là số nguyên 15–120 phút.")
    return raw


def parse_description(raw):
    if raw is None:
        return None
    if not isinstance(raw, str) or len(raw.strip()) > 255:
        raise BookingError("INVALID_DESCRIPTION", "Mô tả phải là chuỗi tối đa 255 ký tự.")
    return raw.strip() or None


def parse_category_id(raw):
    category = db.session.get(Category, positive_id(raw, "category_id"))
    if category is None:
        raise BookingError("CATEGORY_NOT_FOUND", "Không tìm thấy danh mục.", 404)
    if not category.dang_hoat_dong:
        raise BookingError("CATEGORY_UNAVAILABLE", "Danh mục đang ngừng hoạt động.", 409)
    return category.id


PARSERS = {
    "name": parse_name,
    "gia": parse_gia,
    "thoi_luong": parse_thoi_luong,
    "category_id": parse_category_id,
    "description": parse_description,
}


@app.route("/dich-vu")
def trang_dich_vu():
    return render_template('dichVu.html')


@app.get("/api/v1/dich-vu")
def get_dich_vu():
    danh_sach = db.session.execute(dich_vu_hien_thi().order_by(DichVu.id)).scalars().all()
    return jsonify({"data": [dich_vu_to_dict(dv) for dv in danh_sach]}), 200


@app.get("/api/v1/dich-vu/<int:dich_vu_id>")
def get_chi_tiet_dich_vu(dich_vu_id):
    dich_vu = db.session.scalar(dich_vu_hien_thi().where(DichVu.id == dich_vu_id))
    if dich_vu is None:
        return jsonify({"error": {"code": "DICH_VU_NOT_FOUND",
                                  "message": "Không tìm thấy dịch vụ"}}), 404
    return jsonify({"data": dich_vu_to_dict(dich_vu)}), 200


@app.post("/api/v1/dich-vu")
@service_errors
def tao_dich_vu():
    current_account(VaiTro.QUAN_LY)
    data = read_json(set(PARSERS))
    missing = REQUIRED_FIELDS - set(data)
    if missing:
        raise BookingError("MISSING_FIELDS", f"Thiếu trường: {', '.join(sorted(missing))}.")
    dich_vu = DichVu(**{field: PARSERS[field](value) for field, value in data.items()})
    db.session.add(dich_vu)
    db.session.flush()
    result = dich_vu_to_dict(dich_vu)
    db.session.commit()
    return {"data": result}, 201


@app.patch("/api/v1/dich-vu/<int:dich_vu_id>")
@service_errors
def cap_nhat_dich_vu(dich_vu_id):
    current_account(VaiTro.QUAN_LY)
    data = read_json(set(PARSERS) | {"dang_hoat_dong"})
    if not data:
        raise BookingError("EMPTY_BODY", "Cần gửi ít nhất một trường để cập nhật.")
    dich_vu = db.session.get(DichVu, dich_vu_id)
    if dich_vu is None:
        raise BookingError("DICH_VU_NOT_FOUND", "Không tìm thấy dịch vụ.", 404)
    for field, value in data.items():
        if field == "dang_hoat_dong":
            if type(value) is not bool:
                raise BookingError("INVALID_ACTIVE_FLAG", "dang_hoat_dong phải là true/false.")
        else:
            value = PARSERS[field](value)
        setattr(dich_vu, field, value)
    db.session.flush()
    result = dich_vu_to_dict(dich_vu)
    db.session.commit()
    return {"data": result}, 200
