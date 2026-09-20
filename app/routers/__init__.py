from fastapi import FastAPI
from . import (
    auth, users, user_management, leads, lead_details,
    lead_comms, lead_schedule, whatsapp_conversations,
    whatsapp_send, whatsapp_template, whatsapp_media,
    whatsapp_webhook, calls, call_actions, call_media,
    call_webhook, call_ai, campaigns, campaign_execution,
    follow_ups, follow_up_actions, site_visits,
    site_visit_actions, projects, notifications, settings,
    ai, ai_suggest, ai_crm, analytics_dashboard,
    analytics_operations, health
)


ALL_ROUTERS = [
    auth.router, users.router, user_management.router,
    leads.router, lead_details.router, lead_comms.router,
    lead_schedule.router, whatsapp_conversations.router,
    whatsapp_send.router, whatsapp_template.router,
    whatsapp_media.router, whatsapp_webhook.router,
    calls.router, call_actions.router, call_media.router,
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
