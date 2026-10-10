from fastapi import FastAPI

from app.routers import (
    ai,
    ai_crm,
    ai_suggest,
    analytics_dashboard,
    analytics_operations,
    auth,
    call_actions,
    call_ai,
    call_media,
    call_webhook,
    calls_read,
    calls_write,
    campaign_execution,
    campaigns,
    follow_up_actions,
    follow_ups,
    health,
    lead_comms,
    lead_details,
    lead_schedule,
    leads,
    notifications,
    projects,
    settings,
    site_visit_actions,
    site_visits,
    user_management,
    users,
    whatsapp_conversations,
    whatsapp_media,
    whatsapp_send,
    whatsapp_template,
    whatsapp_webhook,
)

ALL_ROUTERS = [
    auth.router, users.router, user_management.router,
    leads.router, lead_details.router, lead_comms.router,
    lead_schedule.router, whatsapp_conversations.router,
    whatsapp_send.router, whatsapp_template.router,
    whatsapp_media.router, whatsapp_webhook.router,
    calls_read.router, calls_write.router, call_actions.router, call_media.router,
    call_webhook.router, call_ai.router, campaigns.router,
    campaign_execution.router, follow_ups.router,
    follow_up_actions.router, site_visits.router,
    site_visit_actions.router, projects.router,
    notifications.router, settings.router, ai.router,
    ai_suggest.router, ai_crm.router,
    analytics_dashboard.router, analytics_operations.router,
    health.router,
]

def register_routers(app: FastAPI):
    for r in ALL_ROUTERS:
        app.include_router(r)
