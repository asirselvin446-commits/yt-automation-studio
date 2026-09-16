from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.schema import AutomationSettings
from app.schemas.dto import AutomationSettingsDTO

router = APIRouter(prefix="/automation", tags=["Automation Center"])


@router.get("", response_model=AutomationSettingsDTO)
async def get_automation_settings(db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(AutomationSettings))
    sett = q.scalar_one_or_none()
    if not sett:
        sett = AutomationSettings()
        db.add(sett)
        await db.commit()
    return AutomationSettingsDTO(
        folder_monitoring=sett.folder_monitoring,
        ai_analysis=sett.ai_analysis,
        metadata_generation=sett.metadata_generation,
        thumbnail_generation=sett.thumbnail_generation,
        approval_required=sett.approval_required,
        auto_upload=sett.auto_upload,
        auto_scheduling=sett.auto_scheduling,
        analytics_sync=sett.analytics_sync,
        ai_insights=sett.ai_insights,
        watch_folder_root=sett.watch_folder_root,
        default_ai_provider=sett.default_ai_provider,
        ai_cost_preset=sett.ai_cost_preset
    )


@router.put("", response_model=AutomationSettingsDTO)
async def update_automation_settings(payload: AutomationSettingsDTO, db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(AutomationSettings))
    sett = q.scalar_one_or_none()
    if not sett:
        sett = AutomationSettings()
        db.add(sett)

    sett.folder_monitoring = payload.folder_monitoring
    sett.ai_analysis = payload.ai_analysis
    sett.metadata_generation = payload.metadata_generation
    sett.thumbnail_generation = payload.thumbnail_generation
    sett.approval_required = payload.approval_required
    sett.auto_upload = payload.auto_upload
    sett.auto_scheduling = payload.auto_scheduling
    sett.analytics_sync = payload.analytics_sync
    sett.ai_insights = payload.ai_insights
    sett.watch_folder_root = payload.watch_folder_root
    sett.default_ai_provider = payload.default_ai_provider
    sett.ai_cost_preset = payload.ai_cost_preset

    await db.commit()
    return payload
