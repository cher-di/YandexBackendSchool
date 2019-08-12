CREATE TABLE IF NOT EXISTS imports
(
    import_id   SERIAL PRIMARY KEY,
    import_time TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS citizens
(
    id         SERIAL,
    import_id  INT         NOT NULL,
    citizen_id INT         NOT NULL,
    town       VARCHAR(70) NOT NULL,
    street     VARCHAR(70) NOT NULL,
    building   VARCHAR(20) NOT NULL,
    apartment  INT         NOT NULL,
    name       VARCHAR(50) NOT NULL,
    birth_date DATE        NOT NULL,
    gender     VARCHAR(6)  NOT NULL CHECK (gender IN ('male', 'female')),
    CONSTRAINT citizens_pk PRIMARY KEY (id),
    CONSTRAINT citizens_fk FOREIGN KEY (import_id) REFERENCES imports (import_id),
    CONSTRAINT citizens_uk UNIQUE (import_id, citizen_id)
);

CREATE TABLE IF NOT EXISTS relatives
(
    id1 INT NOT NULL,
    id2 INT NOT NULL,
    CONSTRAINT relatives_fk_id1 FOREIGN KEY (id1) REFERENCES citizens (id),
    CONSTRAINT relatives_fk_id2 FOREIGN KEY (id2) REFERENCES citizens (id)
);

CREATE INDEX IF NOT EXISTS relatives_idx_1 ON relatives (id1);
CREATE INDEX IF NOT EXISTS relatives_idx_2 ON relatives (id2);
CREATE INDEX IF NOT EXISTS citizens_import_id_idx ON citizens (import_id);