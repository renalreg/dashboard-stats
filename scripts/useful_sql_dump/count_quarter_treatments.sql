SELECT
    B.sendingfacility,
    COUNT(CASE WHEN DATE_TRUNC('month', A.fromtime) = DATE_TRUNC('month', NOW() - INTERVAL '1 month') THEN 1 END) AS starts_1_month_ago,
    COUNT(CASE WHEN DATE_TRUNC('month', A.fromtime) = DATE_TRUNC('month', NOW() - INTERVAL '2 month') THEN 1 END) AS starts_2_months_ago,
    COUNT(CASE WHEN DATE_TRUNC('month', A.fromtime) = DATE_TRUNC('month', NOW() - INTERVAL '3 month') THEN 1 END) AS starts_3_months_ago
FROM treatment A
INNER JOIN patientrecord B ON A.pid = B.pid
WHERE sendingextract = 'UKRDC'
GROUP BY B.sendingfacility
ORDER BY B.sendingfacility;