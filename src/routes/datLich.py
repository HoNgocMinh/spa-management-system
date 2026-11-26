"""Khách gửi yêu cầu; lễ tân phân công và xác nhận để giữ chỗ."""
from datetime import datetime, time, timedelta
from functools import wraps

from flask import render_template, request, session
from sqlalchemy.exc import SQLAlchemyError

from src import app, db
from src.models.models import (
    DichVu, NguonDat, NhanVien, PhieuLichHen, QuyDinh,
    TaiKhoan, TrangThaiDatLich, VaiTro,
)

from src.spa_time import SPA_TZ, now_vn


class BookingError(Exception):
    def __init__(self, code, message, status=400):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def api_error(code, message, status):
    return {"error": {"code": code, "message": message}}, status


def booking_errors(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        try:
            return view(*args, **kwargs)
        except BookingError as error:
            db.session.rollback()
            return api_error(error.code, error.message, error.status)
        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception("Lỗi cơ sở dữ liệu khi xử lý lịch hẹn")
            return api_error("DATABASE_ERROR", "Không thể lưu thay đổi lịch hẹn.", 500)

    return wrapped


def lich_hen_to_dict(lich):
    return {
        "id": lich.id,
        "khach_hang_id": lich.khach_hang_id,
        "dich_vu_id": lich.dich_vu_id,
        "nhan_vien_thuc_hien_id": lich.nhan_vien_thuc_hien_id,
        "bat_dau": lich.bat_dau.replace(tzinfo=SPA_TZ).isoformat(),
        "ket_thuc": lich.ket_thuc.replace(tzinfo=SPA_TZ).isoformat(),
        "nguon_dat": lich.nguon_dat.value,
        "trang_thai": lich.trang_thai.value,
        "ghi_chu": lich.ghi_chu,
    }


def read_json(allowed):
    if not request.is_json:
        raise BookingError("INVALID_CONTENT_TYPE", "Cần gửi application/json.", 415)
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise BookingError("INVALID_JSON", "Cần gửi JSON object hợp lệ.")
    if set(data) - allowed:
        raise BookingError("UNKNOWN_FIELDS", "Có trường không được phép gửi.")
    return data


def positive_id(value, field):
    if type(value) is not int or value <= 0:
        raise BookingError("INVALID_ID", f"{field} phải là số nguyên dương.")
    return value


def current_account(role):
    account_id = session.get("tai_khoan_id")
    if type(account_id) is not int or account_id <= 0:
        raise BookingError("UNAUTHENTICATED", "Bạn cần đăng nhập.", 401)
    account = db.session.get(TaiKhoan, account_id)
    if account is None or not account.dang_hoat_dong:
        raise BookingError("UNAUTHENTICATED", "Tài khoản không hợp lệ hoặc đã khóa.", 401)
    if account.vai_tro != role:
        raise BookingError("FORBIDDEN", "Bạn không có quyền thực hiện thao tác này.", 403)
    return account


def require_active_service(service):
    if service is None:
        raise BookingError("SERVICE_NOT_FOUND", "Không tìm thấy dịch vụ.", 404)
    if not service.dang_hoat_dong or not service.category.dang_hoat_dong:
        raise BookingError("SERVICE_UNAVAILABLE", "Dịch vụ đang ngừng nhận lịch.", 409)


def parse_start_time(raw):
    try:
        if not isinstance(raw, str):
            raise ValueError()
        start = datetime.fromisoformat(raw)
        if start.utcoffset() is None:
            raise ValueError()
        start = start.astimezone(SPA_TZ).replace(tzinfo=None)
        if start.year < 1000:
            raise ValueError()
    except (ValueError, OverflowError):
        raise BookingError("INVALID_START_TIME", "Cần thời gian ISO 8601 có múi giờ.") from None
    if start <= now_vn():
        raise BookingError("START_TIME_IN_PAST", "Giờ hẹn phải nằm trong tương lai.")
    return start


@app.route("/dat-lich", endpoint="trangDatLich")
def trang_dat_lich():
    return render_template("datLich.html")


@app.post("/api/v1/dat-lich")
@booking_errors
def tao_lich_hen():
    account = current_account(VaiTro.KHACH_HANG)
    if account.khach_hang is None:
        raise BookingError("CUSTOMER_PROFILE_REQUIRED", "Chưa có hồ sơ khách hàng.", 409)
    data = read_json({"dich_vu_id", "bat_dau", "ghi_chu"})
    service_id = positive_id(data.get("dich_vu_id"), "dich_vu_id")
    start = parse_start_time(data.get("bat_dau"))
    note = data.get("ghi_chu")
    if note is not None and (not isinstance(note, str) or len(note) > 2000):
        raise BookingError("INVALID_NOTE", "Ghi chú phải là chuỗi tối đa 2000 ký tự.")
    service = db.session.get(DichVu, service_id)
    require_active_service(service)
    try:
        end = start + timedelta(minutes=service.thoi_luong)
    except OverflowError:
        raise BookingError("INVALID_START_TIME", "Giờ kết thúc vượt phạm vi cho phép.") from None
    appointment = PhieuLichHen(
        khach_hang_id=account.khach_hang.id, dich_vu_id=service.id,
        nhan_vien_thuc_hien_id=None, bat_dau=start, ket_thuc=end,
        nguon_dat=NguonDat.ONLINE, nguoi_tao_id=account.id,
        trang_thai=TrangThaiDatLich.DANG_CHO_XAC_NHAN,
        ghi_chu=(note.strip() or None) if note is not None else None,
    )
    db.session.add(appointment)
    db.session.flush()
    result = lich_hen_to_dict(appointment)
    db.session.commit()
    return {"data": result, "message": "Đã nhận yêu cầu, đang chờ xác nhận."}, 201


@app.post("/api/v1/dat-lich/<int:lich_hen_id>/xac-nhan", endpoint="xacNhanDatLich")
@booking_errors
def xac_nhan_dat_lich(lich_hen_id):
    if db.engine.dialect.name == "mysql":
        db.session.connection(execution_options={"isolation_level": "READ COMMITTED"})
    current_account(VaiTro.LE_TAN)
    data = read_json({"nhan_vien_thuc_hien_id"})
    employee_id = positive_id(data.get("nhan_vien_thuc_hien_id"), "nhan_vien_thuc_hien_id")
    employee = db.session.get(NhanVien, employee_id, with_for_update=True, populate_existing=True)
    if employee is None:
        raise BookingError("EMPLOYEE_NOT_FOUND", "Không tìm thấy nhân viên.", 404)
    employee_account = db.session.get(TaiKhoan, employee.tai_khoan_id, with_for_update=True, populate_existing=True)
    if (not employee.dang_hoat_dong or employee_account is None
            or not employee_account.dang_hoat_dong
            or employee_account.vai_tro != VaiTro.KY_THUAT_VIEN):
        raise BookingError("EMPLOYEE_UNAVAILABLE", "Cần kỹ thuật viên đang hoạt động.", 409)
    appointment = db.session.get(PhieuLichHen, lich_hen_id, with_for_update=True, populate_existing=True)
    if appointment is None:
        raise BookingError("APPOINTMENT_NOT_FOUND", "Không tìm thấy lịch hẹn.", 404)
    if appointment.trang_thai != TrangThaiDatLich.DANG_CHO_XAC_NHAN:
        raise BookingError("INVALID_APPOINTMENT_STATE", "Chỉ xác nhận lịch đang chờ.", 409)
    if appointment.bat_dau <= now_vn():
        raise BookingError("START_TIME_IN_PAST", "Lịch hẹn đã quá giờ bắt đầu.", 409)
    require_active_service(appointment.dich_vu)
    limit = db.session.scalar(db.select(QuyDinh.gioi_han_khach_ngay_nvien)
                              .where(QuyDinh.singleton.is_(True)))
    if limit is None:
        raise BookingError("SETTINGS_REQUIRED", "Cần khởi tạo quy định trước khi xác nhận.", 409)

    states = (TrangThaiDatLich.DA_XAC_NHAN, TrangThaiDatLich.DANG_THUC_HIEN,
              TrangThaiDatLich.HOAN_THANH)
    assigned = db.select(PhieuLichHen.id).where(
        PhieuLichHen.nhan_vien_thuc_hien_id == employee_id,
        PhieuLichHen.trang_thai.in_(states),
    )
    overlap = assigned.where(
        PhieuLichHen.bat_dau < appointment.ket_thuc,
        PhieuLichHen.ket_thuc > appointment.bat_dau,
    ).limit(1)
    if db.session.scalar(overlap) is not None:
        raise BookingError("APPOINTMENT_OVERLAP", "Nhân viên đã có lịch trong khoảng giờ này.", 409)

    day = appointment.bat_dau.date()
    day_start = datetime.combine(day, time.min)
    day_end = datetime.combine(day, time.max)
    at_capacity = assigned.where(
        PhieuLichHen.bat_dau.between(day_start, day_end)
    ).offset(limit - 1).limit(1)
    if db.session.scalar(at_capacity) is not None:
        raise BookingError("DAILY_LIMIT_REACHED", "Nhân viên đã đủ lượt khách trong ngày.", 409)
    appointment.nhan_vien_thuc_hien_id = employee_id
    appointment.trang_thai = TrangThaiDatLich.DA_XAC_NHAN
    db.session.flush()
    result = lich_hen_to_dict(appointment)
    db.session.commit()
    # Gửi thông báo sau commit khi project có dịch vụ gửi email.
    return {"data": result, "message": "Đã xác nhận lịch hẹn."}, 200
