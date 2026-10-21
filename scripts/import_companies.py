"""Import issuer identity and optional annual financials from a sourced CSV."""

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import create_app
from app.models import Company, CompanyFinancial, CompanySource, db

REQUIRED = [
    "identifier", "official_name", "official_name_en", "symbol", "sector",
    "description", "products_services", "is_synthetic", "source_url",
]
FINANCIAL_FIELDS = (
    "revenue", "net_income", "total_assets", "total_liabilities",
    "current_assets", "current_liabilities", "market_cap",
)


def import_csv(path: str) -> int:
    app = create_app()
    with app.app_context(), open(path, encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [field for field in REQUIRED if field not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"Missing columns: {', '.join(missing)}")
        count = 0
        for line_number, row in enumerate(reader, start=2):
            source_url = (row.get("source_url") or "").strip()
            if not source_url.startswith("https://"):
                raise ValueError(f"Row {line_number}: source_url must be an official HTTPS source")
            synthetic = (row.get("is_synthetic") or "").strip().lower() in ("1", "true", "yes")
            has_financials = any((row.get(field) or "").strip() for field in FINANCIAL_FIELDS)
            if has_financials and synthetic:
                raise ValueError(f"Row {line_number}: financials in this import must not be synthetic")
            year = (row.get("year") or "").strip()
            if has_financials and not year:
                raise ValueError(f"Row {line_number}: year is required when importing financials")

            company = Company.query.filter_by(symbol=row["symbol"].strip()).first()
            if company is None:
                company = Company.query.filter_by(identifier=row["identifier"].strip()).first()
            if company is None:
                company = Company(
                    identifier=row["identifier"].strip(),
                    official_name=row["official_name"].strip(),
                    official_name_en=row["official_name_en"].strip(),
                    symbol=row["symbol"].strip(),
                    sector=row["sector"].strip(),
                    subsector=(row.get("subsector") or "").strip(),
                    description=row["description"].strip(),
                    products_services=row["products_services"].strip(),
                )
                db.session.add(company)
                db.session.flush()
            company.is_synthetic = synthetic
            company.source_url = source_url
            company.description = row["description"].strip()
            company.products_services = row["products_services"].strip()
            db.session.add(CompanySource(
                company_id=company.id,
                title="Official company information / financial filing",
                url=source_url,
                notes=f"Imported from CSV; financial period: {year or 'not supplied'}.",
            ))

            if has_financials:
                financial = CompanyFinancial.query.filter_by(company_id=company.id, period_year=int(year)).first()
                if financial is None:
                    financial = CompanyFinancial(company_id=company.id, period_year=int(year))
                    db.session.add(financial)
                for field in FINANCIAL_FIELDS:
                    setattr(financial, field, _number(row.get(field)))
                financial.source_url = source_url
                financial.is_synthetic = False
            count += 1
        db.session.commit()
        return count


def _number(value):
    value = (value or "").strip().replace(",", "")
    return float(value) if value else None


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "data" / "companies_demo.csv")
    print(f"Imported/updated {import_csv(path)} company rows")


if __name__ == "__main__":
    main()
