-- VACUUM (recupera espaço e atualiza estatísticas)
VACUUM VERBOSE;

-- REINDEX (reconstrói índices – seguro para produção no PG 12+)
REINDEX DATABASE CONCURRENTLY raijmobi_user_db;

-- Limpeza condicional de logs e tokens (evita erros se tabelas não existirem)
DO $$
BEGIN
    -- easyaudit (auditoria)
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'easyaudit_crudevent') THEN
        DELETE FROM easyaudit_crudevent WHERE datetime < NOW() - INTERVAL '30 days';
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'easyaudit_loginevent') THEN
        DELETE FROM easyaudit_loginevent WHERE datetime < NOW() - INTERVAL '30 days';
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'easyaudit_requestevent') THEN
        DELETE FROM easyaudit_requestevent WHERE datetime < NOW() - INTERVAL '30 days';
    END IF;

    -- token_blacklist (JWT blacklist)
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'token_blacklist_blacklistedtoken') THEN
        DELETE FROM token_blacklist_blacklistedtoken WHERE created_at < NOW() - INTERVAL '30 days';
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'token_blacklist_outstandingtoken') THEN
        DELETE FROM token_blacklist_outstandingtoken WHERE created_at < NOW() - INTERVAL '30 days';
    END IF;
END $$;