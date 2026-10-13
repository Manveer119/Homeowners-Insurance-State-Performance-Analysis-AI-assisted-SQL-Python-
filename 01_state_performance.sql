-- State performance scorecard: volume, conversion, premium, retention, and loss experience.
-- Simplification: each policy is a 12-month term and its written premium is treated as earned.
WITH q AS (
    SELECT state,
           COUNT(*)            AS quotes,
           SUM(bound)          AS binds
    FROM quotes
    GROUP BY state
),
p AS (
    SELECT state,
           COUNT(*)                AS policies,
           SUM(written_premium)    AS written_premium,
           AVG(written_premium)    AS avg_premium,
           AVG(renewed)            AS retention_rate
    FROM policies
    GROUP BY state
),
c AS (
    SELECT pol.state,
           COUNT(cl.claim_id)      AS claims,
           SUM(cl.incurred_loss)   AS incurred_loss
    FROM claims cl
    JOIN policies pol ON pol.policy_id = cl.policy_id
    GROUP BY pol.state
)
SELECT q.state,
       q.quotes,
       q.binds,
       ROUND(1.0 * q.binds / q.quotes, 4)                        AS quote_to_bind,
       p.policies,
       ROUND(p.written_premium, 2)                               AS written_premium,
       ROUND(p.avg_premium, 2)                                   AS avg_premium,
       ROUND(p.retention_rate, 4)                                AS retention_rate,
       COALESCE(c.claims, 0)                                     AS claims,
       ROUND(COALESCE(c.incurred_loss, 0), 2)                    AS incurred_loss,
       ROUND(COALESCE(c.incurred_loss, 0) / p.written_premium, 4) AS loss_ratio,
       ROUND(100.0 * COALESCE(c.claims, 0) / p.policies, 2)      AS claims_per_100_policies,
       ROUND(COALESCE(c.incurred_loss, 0) / NULLIF(c.claims, 0), 2) AS avg_severity
FROM q
JOIN p ON p.state = q.state
LEFT JOIN c ON c.state = q.state
ORDER BY written_premium DESC;
