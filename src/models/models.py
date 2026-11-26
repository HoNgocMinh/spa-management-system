import enum
from decimal import Decimal

from src import db, app
from sqlalchemy import (
    Boolean, CheckConstraint, Column, DateTime, Enum, ForeignKey,
    Index, Integer, Numeric, String, Text,
)
from sqlalchemy.orm import relationship
from src.spa_time import now_vn


class VaiTro(enum.Enum):
    ADMIN = "ADMIN"
    LE_TAN = "LE_TAN"
    THU_NGAN = "THU_NGAN"
    QUAN_LY = "QUAN_LY"
    KHACH_HANG = "KHACH_HANG"
    KY_THUAT_VIEN = "KY_THUAT_VIEN"


class TrangThaiDatLich(enum.Enum):
    DANG_CHO_XAC_NHAN = "DANG_CHO_XAC_NHAN"
    DA_XAC_NHAN = "DA_XAC_NHAN"
    DANG_THUC_HIEN = "DANG_THUC_HIEN"
    HOAN_THANH = "HOAN_THANH"
    DA_HUY = "DA_HUY"
    KHONG_DEN = "KHONG_DEN"


class PhuongThucThanhToan(enum.Enum):
    THE = "THE"
    TIEN_MAT = "TIEN_MAT"
    VI_DIEN_TU = "VI_DIEN_TU"


class TrangThaiThanhToan(enum.Enum):
    CHUA_THANH_TOAN = "CHUA_THANH_TOAN"
    DA_THANH_TOAN = "DA_THANH_TOAN"


class NguonDat(enum.Enum):
    ONLINE = "ONLINE"
    TAI_QUAY = "TAI_QUAY"


class TaiKhoan(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    vai_tro = Column(Enum(VaiTro), nullable=False, default=VaiTro.KHACH_HANG)
    dang_hoat_dong = Column(Boolean, nullable=False, default=True)

    khach_hang = relationship("KhachHang", back_populates="tai_khoan", uselist=False)
    nhan_vien = relationship("NhanVien", back_populates="tai_khoan", uselist=False)

    def __repr__(self):
        return f"<TaiKhoan(id={self.id}, username={self.username}, vai_tro={self.vai_tro})>"


class KhachHang(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    tai_khoan_id = Column(Integer, ForeignKey("tai_khoan.id"), unique=True, nullable=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False, unique=True)
    email = Column(String(120), nullable=True)
    address = Column(String(255), nullable=True)

    phieu_lich_hen = relationship("PhieuLichHen", back_populates="khach_hang")
    hoa_don = relationship("HoaDon", back_populates="khach_hang")
    tai_khoan = relationship("TaiKhoan", back_populates="khach_hang")

    def __repr__(self):
        return f"<KhachHang(id={self.id}, name={self.name}, phone={self.phone})>"


class NhanVien(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    tai_khoan_id = Column(Integer, ForeignKey("tai_khoan.id"), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)
    dang_hoat_dong = Column(Boolean, nullable=False, default=True)

    phieu_lich_hen = relationship("PhieuLichHen", back_populates="nhan_vien_thuc_hien")
    phieu_dich_vu = relationship("PhieuDichVu", back_populates="nhan_vien_lap")
    tai_khoan = relationship("TaiKhoan", back_populates="nhan_vien", uselist=False)

    def __repr__(self):
        return f"<NhanVien(id={self.id}, name={self.name}, tai_khoan_id={self.tai_khoan_id})>"


class Category(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    dang_hoat_dong = Column(Boolean, nullable=False, default=True)
    dich_vu = relationship("DichVu", back_populates="category")

    def __str__(self) -> str:
        return str(self.name)

    def __repr__(self):
        return f"<Category(id={self.id}, name={self.name})>"


class DichVu(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    gia = Column(Numeric(12, 0), nullable=False)
    thoi_luong = Column(Integer, nullable=False)
    description = Column(String(255), nullable=True)
    category_id = Column(Integer, ForeignKey("category.id"), nullable=False)
    dang_hoat_dong = Column(Boolean, nullable=False, default=True)
    version = Column(Integer, nullable=False, default=1)

    __table_args__ = (
        CheckConstraint("thoi_luong >= 15 AND thoi_luong <= 120", name="ck_dich_vu_thoi_luong"),
        CheckConstraint("gia > 0", name="ck_dich_vu_gia"),
        CheckConstraint("version >= 1", name="ck_dich_vu_version"),
    )

    __mapper_args__ = {
        "version_id_col": version,
    }

    phieu_lich_hen = relationship("PhieuLichHen", back_populates="dich_vu")
    phieu_dich_vu = relationship("PhieuDichVu", back_populates="dich_vu")
    chi_tiet_hoa_don = relationship("ChiTietHoaDon", back_populates="dich_vu")
    category = relationship("Category", back_populates="dich_vu")

    def __repr__(self):
        return f"<DichVu(id={self.id}, name={self.name}, gia={self.gia}, thoi_luong={self.thoi_luong})>"


class PhieuLichHen(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    khach_hang_id = Column(Integer, ForeignKey("khach_hang.id"), nullable=False)
    dich_vu_id = Column(Integer, ForeignKey("dich_vu.id"), nullable=False)
    nhan_vien_thuc_hien_id = Column(Integer, ForeignKey("nhan_vien.id"), nullable=True)
    bat_dau = Column(DateTime, nullable=False)
    ket_thuc = Column(DateTime, nullable=False)
    nguon_dat = Column(Enum(NguonDat), nullable=False, default=NguonDat.ONLINE)
    nguoi_tao_id = Column(Integer, ForeignKey("tai_khoan.id"), nullable=True)
    nguoi_tao = relationship("TaiKhoan")
    trang_thai = Column(Enum(TrangThaiDatLich), nullable=False, default=TrangThaiDatLich.DANG_CHO_XAC_NHAN)
    ghi_chu = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=now_vn)

    __table_args__ = (
        Index("ix_phieu_lich_hen_nhan_vien_bat_dau", "nhan_vien_thuc_hien_id", "bat_dau"),
        CheckConstraint("ket_thuc > bat_dau", name="ck_phieu_lich_hen_thoi_gian"),
        CheckConstraint("(trang_thai NOT IN ('DA_XAC_NHAN', 'DANG_THUC_HIEN', 'HOAN_THANH')) OR (nhan_vien_thuc_hien_id IS NOT NULL)", name="ck_phieu_lich_hen_nhan_vien_khi_xac_nhan"),
    )

    phieu_dich_vu = relationship("PhieuDichVu", back_populates="lich_hen", uselist=False)
    khach_hang = relationship("KhachHang", back_populates="phieu_lich_hen")
    dich_vu = relationship("DichVu", back_populates="phieu_lich_hen")
    nhan_vien_thuc_hien = relationship("NhanVien", back_populates="phieu_lich_hen")

    def __repr__(self):
        return f"<PhieuLichHen(id={self.id}, khach_hang_id={self.khach_hang_id}, dich_vu_id={self.dich_vu_id}, bat_dau={self.bat_dau}, ket_thuc={self.ket_thuc})>"


class PhieuDichVu(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    lich_hen_id = Column(Integer, ForeignKey("phieu_lich_hen.id"), nullable=False, unique=True)
    dich_vu_id = Column(Integer, ForeignKey("dich_vu.id"), nullable=False)
    nguoi_lap_id = Column(Integer, ForeignKey("nhan_vien.id"), nullable=False)
    nhan_vien_lap = relationship("NhanVien", foreign_keys=[nguoi_lap_id], back_populates="phieu_dich_vu")
    thoi_luong = Column(Integer, nullable=False)
    gia_dich_vu = Column(Numeric(12, 0), nullable=False)
    ghi_chu = Column(Text, nullable=True)
    phan_hoi_khach_hang = Column(Text, nullable=True)
    hoan_thanh_luc = Column(DateTime, nullable=False)

    __table_args__ = (
        CheckConstraint("gia_dich_vu > 0", name="ck_phieu_dich_vu_gia"),
        CheckConstraint("thoi_luong BETWEEN 15 AND 120", name="ck_phieu_dich_vu_thoi_luong"),
    )

    dich_vu = relationship("DichVu", back_populates="phieu_dich_vu")
    lich_hen = relationship("PhieuLichHen", back_populates="phieu_dich_vu")
    chi_tiet_hoa_don = relationship("ChiTietHoaDon", back_populates="phieu_dich_vu", uselist=False)

    def __repr__(self):
        return f"<PhieuDichVu(id={self.id}, lich_hen_id={self.lich_hen_id}, dich_vu_id={self.dich_vu_id}, gia_dich_vu={self.gia_dich_vu})>"


class HoaDon(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    khach_hang_id = Column(Integer, ForeignKey("khach_hang.id"), nullable=False)
    nguoi_lap_id = Column(Integer, ForeignKey("tai_khoan.id"), nullable=False)
    ngay_lap = Column(DateTime, nullable=False, default=now_vn)
    tong_tien_dich_vu = Column(Numeric(12, 0), nullable=False, default=Decimal("0"))
    tong_giam_gia = Column(Numeric(12, 0), nullable=False, default=Decimal("0"))
    tong_vat = Column(Numeric(12, 0), nullable=False, default=Decimal("0"))
    tong_tien = Column(Numeric(12, 0), nullable=False, default=Decimal("0"))
    trang_thai_thanh_toan = Column(Enum(TrangThaiThanhToan), nullable=False, default=TrangThaiThanhToan.CHUA_THANH_TOAN)
    phuong_thuc_thanh_toan = Column(Enum(PhuongThucThanhToan), nullable=True)
    thanh_toan_luc = Column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint("tong_tien_dich_vu >= 0", name="ck_hoa_don_tong_tien_dich_vu"),
        CheckConstraint("tong_giam_gia >= 0", name="ck_hoa_don_tong_giam_gia"),
        CheckConstraint("tong_giam_gia <= tong_tien_dich_vu", name="ck_hoa_don_giam_khong_qua_tong"),
        CheckConstraint("tong_vat >= 0", name="ck_hoa_don_tong_vat"),
        CheckConstraint("tong_tien = tong_tien_dich_vu - tong_giam_gia + tong_vat"),
        CheckConstraint("tong_tien >= 0", name="ck_hoa_don_tong_tien"),
        CheckConstraint("thanh_toan_luc IS NULL OR thanh_toan_luc >= ngay_lap",
                        name="ck_hoa_don_ngay_thanh_toan"),
        CheckConstraint(
            "(trang_thai_thanh_toan <> 'DA_THANH_TOAN' "
            " AND thanh_toan_luc IS NULL AND phuong_thuc_thanh_toan IS NULL) "
            "OR "
            "(trang_thai_thanh_toan = 'DA_THANH_TOAN' "
            " AND thanh_toan_luc IS NOT NULL AND phuong_thuc_thanh_toan IS NOT NULL)",
            name="ck_hoa_don_thanh_toan_nhat_quan",
        ),

        Index("ix_hoa_don_khach_hang", "khach_hang_id"),
        Index("ix_hoa_don_thanh_toan", "trang_thai_thanh_toan", "thanh_toan_luc"),
    )

    nguoi_lap = relationship("TaiKhoan", foreign_keys=[nguoi_lap_id])
    chi_tiet_hoa_don = relationship("ChiTietHoaDon", back_populates="hoa_don")
    khach_hang = relationship("KhachHang", back_populates="hoa_don")

    def __repr__(self):
        return f"<HoaDon(id={self.id}, khach_hang_id={self.khach_hang_id}, tong_tien={self.tong_tien})>"


class ChiTietHoaDon(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    hoa_don_id = Column(Integer, ForeignKey("hoa_don.id"), nullable=False)
    phieu_dich_vu_id = Column(Integer, ForeignKey("phieu_dich_vu.id"), nullable=False, unique=True)
    dich_vu_id = Column(Integer, ForeignKey("dich_vu.id"), nullable=False)
    ten_dich_vu = Column(String(100), nullable=False)
    don_gia = Column(Numeric(12, 0), nullable=False)
    ty_le_giam_gia = Column(Numeric(5, 2), nullable=False, default=Decimal("0"))
    tien_giam = Column(Numeric(12, 0), nullable=False, default=Decimal("0"))
    ty_le_vat = Column(Numeric(5, 2), nullable=False)
    tien_vat = Column(Numeric(12, 0), nullable=False, default=Decimal("0"))
    thanh_tien = Column(Numeric(12, 0), nullable=False, default=Decimal("0"))

    __table_args__ = (
        CheckConstraint("don_gia >= 0", name="ck_chi_tiet_don_gia"),
        CheckConstraint("ty_le_giam_gia BETWEEN 0 AND 100", name="ck_chi_tiet_ty_le_giam_gia"),
        CheckConstraint("tien_giam <= don_gia", name="ck_tien_giam_khong_qua_don_gia"),
        CheckConstraint("tien_giam >= 0", name="ck_tien_giam_khong_duoi_0"),
        CheckConstraint("ty_le_vat BETWEEN 0 AND 100", name="ck_chi_tiet_ty_le_vat"),
        CheckConstraint("tien_vat >= 0", name="ck_chi_tiet_tien_vat"),
        CheckConstraint("thanh_tien = don_gia - tien_giam + tien_vat"),
        CheckConstraint("thanh_tien >= 0", name="ck_chi_tiet_thanh_tien")
    )

    hoa_don = relationship("HoaDon", back_populates="chi_tiet_hoa_don")
    phieu_dich_vu = relationship("PhieuDichVu", back_populates="chi_tiet_hoa_don")
    dich_vu = relationship("DichVu", back_populates="chi_tiet_hoa_don")

    def __repr__(self):
        return f"<ChiTietHoaDon(id={self.id}, hoa_don_id={self.hoa_don_id}, ten_dich_vu={self.ten_dich_vu}, thanh_tien={self.thanh_tien})>"


class QuyDinh(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    singleton = Column(Boolean, nullable=False, default=True, unique=True)
    ty_le_vat = Column(Numeric(5, 2), nullable=False, default=Decimal("10"))
    gioi_han_khach_ngay_nvien = Column(Integer, nullable=False, default=5)
    ty_le_giam_gia_toi_da = Column(Numeric(5, 2), nullable=False, default=Decimal("20"))
    updated_at = Column(DateTime, nullable=False, default=now_vn, onupdate=now_vn)
    updated_by_id = Column(Integer, ForeignKey("tai_khoan.id"), nullable=True)

    __table_args__ = (
        CheckConstraint("singleton = 1", name="ck_quy_dinh_singleton"),
        CheckConstraint("ty_le_vat BETWEEN 0 AND 100", name="ck_quy_dinh_ty_le_vat"),
        CheckConstraint("gioi_han_khach_ngay_nvien > 0", name="ck_quy_dinh_gioi_han"),
        CheckConstraint("ty_le_giam_gia_toi_da BETWEEN 0 AND 100", name="ck_quy_dinh_ty_le_giam_gia_toi_da"),
    )

    nguoi_cap_nhat = relationship("TaiKhoan", foreign_keys=[updated_by_id])

    def __repr__(self):
        return f"<QuyDinh(id={self.id}, ty_le_vat={self.ty_le_vat}, gioi_han_khach_ngay_nvien={self.gioi_han_khach_ngay_nvien})>"

if __name__ == "__main__":
    with app.app_context():
        db.create_all()