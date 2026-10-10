-- ==============================================================================
-- Migration Script: scripts/normalise_phones.sql
-- Description: Normalises lead phone numbers to E.164 and checks for duplicates
--              before adding a unique index on leads(phone).
-- ==============================================================================

-- STEP 1: REPORT DUPLICATES (Run this first to verify duplicate leads)
-- This query computes normalised phone numbers and reports if any duplicates exist.
-- DO NOT automatically delete duplicate rows. Review reported IDs and resolve manually.

WITH cleaned_leads AS (
    SELECT
        id,
        name,
        phone,
        email,
        created_at,
        CASE
            -- Standard Indian E.164: +91XXXXXXXXXX
            WHEN regexp_replace(phone, '[\s\-().]', '', 'g') ~ '^\+91[6-9][0-9]{9}$'
                THEN regexp_replace(phone, '[\s\-().]', '', 'g')
            -- Indian with 91 prefix without plus: 91XXXXXXXXXX
            WHEN regexp_replace(phone, '[\s\-().]', '', 'g') ~ '^91[6-9][0-9]{9}$'
                THEN '+' || regexp_replace(phone, '[\s\-().]', '', 'g')
            -- Indian 10-digit with leading 0: 0XXXXXXXXXX
            WHEN regexp_replace(phone, '[\s\-().]', '', 'g') ~ '^0[6-9][0-9]{9}$'
                THEN '+91' || SUBSTRING(regexp_replace(phone, '[\s\-().]', '', 'g') FROM 2)
            -- Indian standard 10-digit: XXXXXXXXXX
            WHEN regexp_replace(phone, '[\s\-().]', '', 'g') ~ '^[6-9][0-9]{9}$'
                THEN '+91' || regexp_replace(phone, '[\s\-().]', '', 'g')
            -- General international numbers with + prefix
            WHEN regexp_replace(phone, '[\s\-().]', '', 'g') ~ '^\+[1-9][0-9]{6,14}$'
                THEN regexp_replace(phone, '[\s\-().]', '', 'g')
            -- Fallback
            ELSE regexp_replace(phone, '[\s\-().]', '', 'g')
        END AS normalised_phone
    FROM leads
)
SELECT
    normalised_phone,
    COUNT(*) AS duplicate_count,
    array_agg(id) AS lead_ids,
    array_agg(name) AS lead_names,
    array_agg(phone) AS original_phones
FROM cleaned_leads
GROUP BY normalised_phone
HAVING COUNT(*) > 1;

-- ==============================================================================
-- STEP 2: NORMALISE EXISTING LEADS IN DATABASE
-- (Execute only after confirming no duplicates from Step 1)
-- ==============================================================================

UPDATE leads
SET phone = CASE
    WHEN regexp_replace(phone, '[\s\-().]', '', 'g') ~ '^\+91[6-9][0-9]{9}$'
        THEN regexp_replace(phone, '[\s\-().]', '', 'g')
    WHEN regexp_replace(phone, '[\s\-().]', '', 'g') ~ '^91[6-9][0-9]{9}$'
        THEN '+' || regexp_replace(phone, '[\s\-().]', '', 'g')
    WHEN regexp_replace(phone, '[\s\-().]', '', 'g') ~ '^0[6-9][0-9]{9}$'
        THEN '+91' || SUBSTRING(regexp_replace(phone, '[\s\-().]', '', 'g') FROM 2)
    WHEN regexp_replace(phone, '[\s\-().]', '', 'g') ~ '^[6-9][0-9]{9}$'
        THEN '+91' || regexp_replace(phone, '[\s\-().]', '', 'g')
    WHEN regexp_replace(phone, '[\s\-().]', '', 'g') ~ '^\+[1-9][0-9]{6,14}$'
        THEN regexp_replace(phone, '[\s\-().]', '', 'g')
    ELSE regexp_replace(phone, '[\s\-().]', '', 'g')
END
WHERE phone IS NOT NULL;

-- Also normalise phone numbers in related tables (conversations, calls, campaign recipients)
UPDATE whatsapp_conversations
SET phone_number = CASE
    WHEN regexp_replace(phone_number, '[\s\-().]', '', 'g') ~ '^\+91[6-9][0-9]{9}$'
        THEN regexp_replace(phone_number, '[\s\-().]', '', 'g')
    WHEN regexp_replace(phone_number, '[\s\-().]', '', 'g') ~ '^91[6-9][0-9]{9}$'
        THEN '+' || regexp_replace(phone_number, '[\s\-().]', '', 'g')
    WHEN regexp_replace(phone_number, '[\s\-().]', '', 'g') ~ '^0[6-9][0-9]{9}$'
        THEN '+91' || SUBSTRING(regexp_replace(phone_number, '[\s\-().]', '', 'g') FROM 2)
    WHEN regexp_replace(phone_number, '[\s\-().]', '', 'g') ~ '^[6-9][0-9]{9}$'
        THEN '+91' || regexp_replace(phone_number, '[\s\-().]', '', 'g')
    WHEN regexp_replace(phone_number, '[\s\-().]', '', 'g') ~ '^\+[1-9][0-9]{6,14}$'
        THEN regexp_replace(phone_number, '[\s\-().]', '', 'g')
    ELSE regexp_replace(phone_number, '[\s\-().]', '', 'g')
END
WHERE phone_number IS NOT NULL;

UPDATE calls
SET phone_number = CASE
    WHEN regexp_replace(phone_number, '[\s\-().]', '', 'g') ~ '^\+91[6-9][0-9]{9}$'
        THEN regexp_replace(phone_number, '[\s\-().]', '', 'g')
    WHEN regexp_replace(phone_number, '[\s\-().]', '', 'g') ~ '^91[6-9][0-9]{9}$'
        THEN '+' || regexp_replace(phone_number, '[\s\-().]', '', 'g')
    WHEN regexp_replace(phone_number, '[\s\-().]', '', 'g') ~ '^0[6-9][0-9]{9}$'
        THEN '+91' || SUBSTRING(regexp_replace(phone_number, '[\s\-().]', '', 'g') FROM 2)
    WHEN regexp_replace(phone_number, '[\s\-().]', '', 'g') ~ '^[6-9][0-9]{9}$'
        THEN '+91' || regexp_replace(phone_number, '[\s\-().]', '', 'g')
    WHEN regexp_replace(phone_number, '[\s\-().]', '', 'g') ~ '^\+[1-9][0-9]{6,14}$'
        THEN regexp_replace(phone_number, '[\s\-().]', '', 'g')
    ELSE regexp_replace(phone_number, '[\s\-().]', '', 'g')
END
WHERE phone_number IS NOT NULL;

-- ==============================================================================
-- STEP 3: ADD UNIQUE CONSTRAINT ON LEADS(PHONE)
-- ==============================================================================
CREATE UNIQUE INDEX IF NOT EXISTS uq_leads_phone ON leads (phone);
