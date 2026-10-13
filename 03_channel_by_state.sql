-- Quote-to-bind conversion and retention by distribution channel within each state.
WITH q AS (
    SELECT state, channel,
           COUNT(*)   AS quotes,
           SUM(bound) AS binds
    FROM quotes
    GROUP BY state, channel
),
p AS (
    SELECT state, channel,
           AVG(renewed) AS retention_rate
    FROM policies
    GROUP BY state, channel
)
SELECT q.state,
       q.channel,
       q.quotes,
       q.binds,
       ROUND(1.0 * q.binds / q.quotes, 4) AS quote_to_bind,
       ROUND(p.retention_rate, 4)         AS retention_rate
FROM q
LEFT JOIN p ON p.state = q.state AND p.channel = q.channel
ORDER BY q.state, q.channel;
