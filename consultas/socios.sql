SELECT
    cnpj_basico,
    nome_socio,
    qualificacao_socio,
    data_entrada_sociedade
FROM socios
ORDER BY data_entrada_sociedade DESC
LIMIT 100;
