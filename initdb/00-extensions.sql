-- Run once by the postgres entrypoint, on an empty PGDATA only
-- (docker-entrypoint-initdb.d). Must come before alembic: revision
-- 675f3d3e99af adds named_area.geom_mpoly, which needs PostGIS to exist.
--
-- Files in this directory run in filename order, so a database dump dropped in
-- here as dump-*.sql.gz still loads after this one.
CREATE EXTENSION IF NOT EXISTS postgis;
