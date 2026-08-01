SELECT
    cnpj_basico,
    razao_social,
    porte_empresa,
    capital_social
FROM empresas
ORDER BY razao_social
LIMIT 100;
