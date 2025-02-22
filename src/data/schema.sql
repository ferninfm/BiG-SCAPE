-- SQLite3 schema for storage and manipulation of bigslice data

-- schema ver.: 1.0.1
CREATE TABLE IF NOT EXISTS schema (
    ver VARCHAR(10) PRIMARY KEY
);
INSERT OR IGNORE INTO schema VALUES('1.0.1');

-- dataset
CREATE TABLE IF NOT EXISTS dataset (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(250) NOT NULL UNIQUE,
    orig_folder VARCHAR(250) NOT NULL,
    description VARCHAR(2500) NOT NULL
);
CREATE INDEX IF NOT EXISTS dataset_name ON dataset(name);
CREATE INDEX IF NOT EXISTS dataset_name ON dataset(orig_folder);

-- bgc
CREATE TABLE IF NOT EXISTS bgc (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id INTEGER NOT NULL,
    name VARCHAR(250) NOT NULL,
    type VARCHAR(10) NOT NULL,
    on_contig_edge BOOLEAN,
    length_nt INTEGER NOT NULL,
    orig_folder VARCHAR(1500) NOT NULL,
    orig_filename VARCHAR(1500) NOT NULL,
    bigscape_product VARCHAR(300),
    bigscape_organism VARCHAR(300),
    UNIQUE(orig_folder, orig_filename, dataset_id),
    FOREIGN KEY(dataset_id) REFERENCES dataset(id),
    FOREIGN KEY(type) REFERENCES enum_bgc_type(code)
);
CREATE INDEX IF NOT EXISTS bgc_dataset ON bgc(dataset_id);
CREATE INDEX IF NOT EXISTS bgc_name ON bgc(name);
CREATE INDEX IF NOT EXISTS bgc_type ON bgc(type);
CREATE INDEX IF NOT EXISTS bgc_gbkpath ON bgc(orig_folder, orig_filename);
CREATE INDEX IF NOT EXISTS bgc_filename ON bgc(orig_filename);
CREATE INDEX IF NOT EXISTS bgc_contigedge ON bgc(on_contig_edge);
CREATE INDEX IF NOT EXISTS bgc_length ON bgc(length_nt);

-- enum_bgc_type
CREATE TABLE IF NOT EXISTS enum_bgc_type (
    code VARCHAR(10) PRIMARY KEY,
    description VARCHAR(250)
);
INSERT OR IGNORE INTO enum_bgc_type VALUES ('as4', 'antiSMASH4 clusterXXX.gbk');
INSERT OR IGNORE INTO enum_bgc_type VALUES ('as5', 'antiSMASH5 regionXXX.gbk');
INSERT OR IGNORE INTO enum_bgc_type VALUES ('mibig', 'MIBiG >= 2.0 gbk');

-- cds
CREATE TABLE IF NOT EXISTS cds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bgc_id INTEGER NOT NULL,
    orf_id INTEGER NOT NULL,
    nt_start INTEGER NOT NULL,
    nt_end INTEGER NOT NULL,
    strand INTEGER CHECK(strand IN (-1,0,1)),
    locus_tag VARCHAR(100),
    protein_id VARCHAR(100),
    product VARCHAR(100),
    biosynthetic BOOLEAN NOT NULL,
    aa_seq TEXT NOT NULL,
    FOREIGN KEY(bgc_id) REFERENCES bgc(id)
    UNIQUE (bgc_id, orf_id)
);
CREATE INDEX IF NOT EXISTS cds_bgc ON cds(bgc_id,orf_id,nt_start,nt_end);

-- hmm
CREATE TABLE IF NOT EXISTS hmm (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    accession VARCHAR(10),
    name VARCHAR(25) NOT NULL,
    model_length INTEGER NOT NULL,
    model_type INTEGER NOT NULL REFERENCES enum_bigslice_type(id),
    UNIQUE(accession, name, model_length)
);

-- bigslice_type
CREATE TABLE IF NOT EXISTS enum_bigslice_type (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE
);
INSERT OR IGNORE INTO enum_bigslice_type VALUES (0, 'BIGSCAPE_PFAM');
INSERT OR IGNORE INTO enum_bigslice_type VALUES (1, 'PFAM_BOTH');
INSERT OR IGNORE INTO enum_bigslice_type VALUES (2, 'BIGSLICE_PFAM');
INSERT OR IGNORE INTO enum_bigslice_type VALUES (3, 'BIGSLICE_SUBPFAM');

-- subpfam
CREATE TABLE IF NOT EXISTS subpfam (
    hmm_id INTEGER NOT NULL,
    parent_hmm_id INTEGER NOT NULL,
    FOREIGN KEY(hmm_id) REFERENCES hmm(id),
    FOREIGN KEY(parent_hmm_id) REFERENCES hmm(id)
);
CREATE INDEX IF NOT EXISTS subpfam_parenthmm ON subpfam(parent_hmm_id, hmm_id);

-- hsp
CREATE TABLE IF NOT EXISTS hsp (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    serial_nr INTEGER NOT NULL,
    cds_id INTEGER NOT NULL,
    hmm_id INTEGER NOT NULL,
    bitscore REAL NOT NULL,
    FOREIGN KEY(cds_id) REFERENCES cds(id),
    FOREIGN KEY(hmm_id) REFERENCES hmm(id),
    UNIQUE(serial_nr, cds_id, hmm_id)
);
CREATE INDEX IF NOT EXISTS hsp_cdshmm ON hsp(serial_nr, cds_id, hmm_id);
CREATE INDEX IF NOT EXISTS hsp_bitscore ON hsp(bitscore);

-- hsp_bigslice
CREATE TABLE IF NOT EXISTS hsp_bigslice (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    serial_nr INTEGER NOT NULL,
    cds_id INTEGER NOT NULL,
    hmm_id INTEGER NOT NULL,
    bitscore REAL NOT NULL,
    FOREIGN KEY(cds_id) REFERENCES cds(id),
    FOREIGN KEY(hmm_id) REFERENCES hmm(id),
    UNIQUE(serial_nr, cds_id, hmm_id)
);
CREATE INDEX IF NOT EXISTS hsp_bigslice_cdshmm ON hsp(serial_nr, cds_id, hmm_id);
CREATE INDEX IF NOT EXISTS hsp_bigslice_bitscore ON hsp(bitscore);

-- hsp_alignment
CREATE TABLE IF NOT EXISTS hsp_alignment (
    hsp_id INTEGER UNIQUE NOT NULL,
    env_start INTEGER NOT NULL,
    env_end INTEGER NOT NULL,
    model_start INTEGER NOT NULL,
    model_end INTEGER NOT NULL,
    model_gaps TEXT NOT NULL,
    cds_start INTEGER NOT NULL,
    cds_end INTEGER NOT NULL,
    cds_gaps TEXT NOT NULL,
    FOREIGN KEY(hsp_id) REFERENCES hsp(id)
);
CREATE INDEX IF NOT EXISTS hspalign_id ON hsp_alignment(hsp_id);
CREATE INDEX IF NOT EXISTS hspalign_model ON hsp_alignment(model_start);
CREATE INDEX IF NOT EXISTS hspalign_cds ON hsp_alignment(cds_start);

-- hsp_subpfam
CREATE TABLE IF NOT EXISTS hsp_subpfam (
    hsp_subpfam_id INTEGER NOT NULL,
    hsp_parent_id INTEGER NOT NULL,
    UNIQUE(hsp_subpfam_id, hsp_parent_id),
    FOREIGN KEY(hsp_subpfam_id) REFERENCES hsp(id),
    FOREIGN KEY(hsp_parent_id) REFERENCES hsp(id)
);
CREATE INDEX IF NOT EXISTS hspsubpfam_parent ON hsp_subpfam(hsp_parent_id, hsp_subpfam_id);
CREATE INDEX IF NOT EXISTS hspsubpfam_sub ON hsp_subpfam(hsp_subpfam_id, hsp_parent_id);

-- msa
CREATE TABLE IF NOT EXISTS msa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cds_id INTEGER NOT NULL,
    hmm_id INTEGER NOT NULL,
    env_start INTEGER NOT NULL,
    env_end INTEGER NOT NULL,
    algn_string TEXT NOT NULL,
    UNIQUE (cds_id, hmm_id, env_start, env_end),
    FOREIGN KEY(cds_id) REFERENCES cds(id),
    FOREIGN KEY(hmm_id) REFERENCES hmm(id)    
);
CREATE INDEX IF NOT EXISTS msa_cdshmm ON msa(cds_id, hmm_id);
CREATE INDEX IF NOT EXISTS msa_bitscore ON hsp(bitscore);

-- taxon_class
CREATE TABLE IF NOT EXISTS taxon_class (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level INTEGER NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL UNIQUE
);
INSERT OR IGNORE INTO taxon_class VALUES (NULL, 0, 'Kingdom');
INSERT OR IGNORE INTO taxon_class VALUES (NULL, 1, 'Phylum');
INSERT OR IGNORE INTO taxon_class VALUES (NULL, 2, 'Class');
INSERT OR IGNORE INTO taxon_class VALUES (NULL, 3, 'Order');
INSERT OR IGNORE INTO taxon_class VALUES (NULL, 4, 'Family');
INSERT OR IGNORE INTO taxon_class VALUES (NULL, 5, 'Genus');
INSERT OR IGNORE INTO taxon_class VALUES (NULL, 6, 'Species');
INSERT OR IGNORE INTO taxon_class VALUES (NULL, 7, 'Organism');
CREATE UNIQUE INDEX IF NOT EXISTS taxon_class_level ON taxon_class(level);
CREATE UNIQUE INDEX IF NOT EXISTS taxon_class_name ON taxon_class(name);

-- taxon
CREATE TABLE IF NOT EXISTS taxon (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    UNIQUE(name, level),
    FOREIGN KEY(level) REFERENCES taxon_class(level)
);
CREATE INDEX IF NOT EXISTS taxon_level ON taxon(level, name);
CREATE INDEX IF NOT EXISTS taxon_name ON taxon(name, level);

-- bgc_taxonomy
CREATE TABLE IF NOT EXISTS bgc_taxonomy (
    bgc_id INTEGER NOT NULL,
    taxon_id INTEGER NOT NULL,
    FOREIGN KEY(bgc_id) REFERENCES bgc(id),
    FOREIGN KEY(taxon_id) REFERENCES taxon(id)
);
CREATE INDEX IF NOT EXISTS bgctaxonomy_bgcid ON bgc_taxonomy(bgc_id);
CREATE INDEX IF NOT EXISTS bgctaxonomy_taxid ON bgc_taxonomy(taxon_id);

-- chem_class
CREATE TABLE IF NOT EXISTS chem_class (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE
);
INSERT OR IGNORE INTO chem_class VALUES (NULL, 'Unknown');
INSERT OR IGNORE INTO chem_class VALUES (NULL, 'Other');
INSERT OR IGNORE INTO chem_class VALUES (NULL, 'Alkaloid');
INSERT OR IGNORE INTO chem_class VALUES (NULL, 'NRP');
INSERT OR IGNORE INTO chem_class VALUES (NULL, 'Polyketide');
INSERT OR IGNORE INTO chem_class VALUES (NULL, 'RiPP');
INSERT OR IGNORE INTO chem_class VALUES (NULL, 'Saccharide');
INSERT OR IGNORE INTO chem_class VALUES (NULL, 'Terpene');
CREATE UNIQUE INDEX IF NOT EXISTS chemclass_name ON chem_class(name);

-- chem_subclass
CREATE TABLE IF NOT EXISTS chem_subclass (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    FOREIGN KEY(class_id) REFERENCES chem_class(id)
);
CREATE INDEX IF NOT EXISTS chemsubclass_name ON chem_subclass(name, class_id);
CREATE INDEX IF NOT EXISTS chemsubclass_class ON chem_subclass(class_id, name);


-- chem_subclass_map
CREATE TABLE IF NOT EXISTS chem_subclass_map (
    class_source VARCHAR(100) NOT NULL,
    type_source VARCHAR(10) NOT NULL,    
    subclass_id INTEGER NOT NULL,
    FOREIGN KEY(type_source) REFERENCES enum_bgc_type(code),
    FOREIGN KEY(subclass_id) REFERENCES chem_subclass(id)
);
CREATE INDEX IF NOT EXISTS chemsubclassmap_source ON chem_subclass_map(type_source, class_source);

-- bgc_class
CREATE TABLE IF NOT EXISTS bgc_class (
    bgc_id INTEGER NOT NULL,
    chem_subclass_id INTEGER NOT NULL,
    FOREIGN KEY(bgc_id) REFERENCES bgc(id),
    FOREIGN KEY(chem_subclass_id) REFERENCES chem_subclass(id)
);
CREATE INDEX IF NOT EXISTS bgcclass_chemsubclass ON bgc_class(chem_subclass_id, bgc_id);
CREATE INDEX IF NOT EXISTS bgcclass_bgc ON bgc_class(bgc_id, chem_subclass_id);

-- enum_run_status
CREATE TABLE IF NOT EXISTS enum_run_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE
);
INSERT OR IGNORE INTO enum_run_status VALUES (1, 'RUN_STARTED');
INSERT OR IGNORE INTO enum_run_status VALUES (2, 'FULL_HMM_SCANNED');
INSERT OR IGNORE INTO enum_run_status VALUES (3, 'MSA_FINISHED');
INSERT OR IGNORE INTO enum_run_status VALUES (4, 'SUBPFAM_SCANNED');
INSERT OR IGNORE INTO enum_run_status VALUES (5, 'FEATURES_EXTRACTED');
INSERT OR IGNORE INTO enum_run_status VALUES (6, 'CLUSTERING_FINISHED');
INSERT OR IGNORE INTO enum_run_status VALUES (7, 'RUN_FINISHED');
CREATE UNIQUE INDEX IF NOT EXISTS enumrunstatus_name ON enum_run_status(name);

-- enum_bgc_status
CREATE TABLE IF NOT EXISTS enum_bgc_status (
    id INTEGER PRIMARY KEY UNIQUE,
    name VARCHAR(100) NOT NULL UNIQUE
);
INSERT OR IGNORE INTO enum_bgc_status VALUES (1, 'LOADED');
INSERT OR IGNORE INTO enum_bgc_status VALUES (2, 'FULL_HMM_SCANNED');
INSERT OR IGNORE INTO enum_bgc_status VALUES (3, 'SUBPFAM_SCANNED');
INSERT OR IGNORE INTO enum_bgc_status VALUES (4, 'FEATURES_EXTRACTED');
CREATE UNIQUE INDEX IF NOT EXISTS enumbgcstatus_name ON enum_bgc_status(name);

-- bgc_status
CREATE TABLE IF NOT EXISTS bgc_status (
    bgc_id INTEGER NOT NULL,
    status INTEGER NOT NULL,
    UNIQUE(bgc_id)
    FOREIGN KEY(bgc_id) REFERENCES bgc(id),
    FOREIGN KEY(status) REFERENCES enum_bgc_status(id)
);
CREATE INDEX IF NOT EXISTS bgc_id_status ON bgc_status(bgc_id, status);

-- bgc_features
CREATE TABLE IF NOT EXISTS bgc_features (
    bgc_id INTEGER NOT NULL,
    hmm_id INTEGER NOT NULL,
    value INTEGER NOT NULL,
    UNIQUE(bgc_id, hmm_id),
    FOREIGN KEY(bgc_id) REFERENCES bgc(id),
    FOREIGN KEY(hmm_id) REFERENCES hmm(id)
);
CREATE INDEX IF NOT EXISTS bgc_features_bgc ON bgc_features(bgc_id, hmm_id, value);
CREATE INDEX IF NOT EXISTS bgc_features_bgc_value ON bgc_features(value, bgc_id, hmm_id);
CREATE INDEX IF NOT EXISTS bgc_features_hmm ON bgc_features(hmm_id, bgc_id, value);
CREATE INDEX IF NOT EXISTS bgc_features_hmm_value ON bgc_features(value, hmm_id, bgc_id);
