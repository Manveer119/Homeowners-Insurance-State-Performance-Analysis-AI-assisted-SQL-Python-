-- Loss experience by roof age band and coastal exposure.
-- Claims are aggregated per policy first so policies with multiple claims
-- don't duplicate premium in the join.
WITH claim_totals AS (
    SELECT policy_id,
           COUNT(*)           AS claims,
           SUM(incurred_loss) AS incurred_loss
    FROM claims
    GROUP BY policy_id
)
SELECT p.roof_age_band,
       p.coastal_zone,
       COUNT(*)                                                   AS policies,
       ROUND(SUM(p.written_premium), 2)                           AS written_premium,
       COALESCE(SUM(ct.claims), 0)                                AS claims,
       ROUND(COALESCE(SUM(ct.incurred_loss), 0), 2)               AS incurred_loss,
       ROUND(COALESCE(SUM(ct.incurred_loss), 0) / SUM(p.written_premium), 4) AS loss_ratio
FROM policies p
LEFT JOIN claim_totals ct ON ct.policy_id = p.policy_id
GROUP BY p.roof_age_band, p.coastal_zone
ORDER BY p.coastal_zone,
         CASE p.roof_age_band          -- explicit order: text sort would put '6-10' after '21+'
             WHEN '0-5'   THEN 1
             WHEN '6-10'  THEN 2
             WHEN '11-15' THEN 3
             WHEN '16-20' THEN 4
             WHEN '21+'   THEN 5
         END;
