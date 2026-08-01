SELECT
    e.cnpj_basico,
    emp.razao_social,
    e.nome_fantasia,
    e.uf,
    e.municipio,
    e.situacao_cadastral
FROM estabelecimentos e
JOIN empresas emp USING (cnpj_basico)
WHERE e.situacao_cadastral = '02'  -- 02 = ATIVA
LIMIT 100;
