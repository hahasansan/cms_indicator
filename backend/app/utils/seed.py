from __future__ import annotations

from sqlalchemy.orm import Session

from app.entity.models import IndicatorCategory


def init_database(db: Session) -> None:
    if not db.query(IndicatorCategory).first():
        db.add_all(
            [
                IndicatorCategory(id="root", name="全部指标", parent_id="root", sort_order=0, enabled=True),
                IndicatorCategory(id="bond", name="债券业务", parent_id="root", sort_order=10, enabled=True),
                IndicatorCategory(id="fund", name="资金业务", parent_id="root", sort_order=20, enabled=True),
            ]
        )
    db.commit()
