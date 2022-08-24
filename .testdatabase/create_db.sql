--
-- PostgreSQL database dump
--

-- Dumped from database version 9.6.18
-- Dumped by pg_dump version 14.4

-- Started on 2022-08-24 06:28:39

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- TOC entry 9 (class 2615 OID 4791977)
-- Name: extract; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA "extract";


ALTER SCHEMA "extract" OWNER TO postgres;

--
-- TOC entry 14 (class 2615 OID 20045564)
-- Name: ukrdc-live; Type: SCHEMA; Schema: -; Owner: ukrdc
--

CREATE SCHEMA "ukrdc-live";


ALTER SCHEMA "ukrdc-live" OWNER TO ukrdc;

--
-- TOC entry 2 (class 3079 OID 8835284)
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- TOC entry 3517 (class 0 OID 0)
-- Dependencies: 2
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- TOC entry 581 (class 1247 OID 4791979)
-- Name: gp_type; Type: TYPE; Schema: extract; Owner: ukrdc
--

CREATE TYPE "extract".gp_type AS ENUM (
    'GP',
    'PRACTICE'
);


ALTER TYPE "extract".gp_type OWNER TO ukrdc;

--
-- TOC entry 300 (class 1255 OID 15156574)
-- Name: trigger_fnc_set_laborder_repository_update_date(); Type: FUNCTION; Schema: extract; Owner: ukrdc
--

CREATE FUNCTION "extract".trigger_fnc_set_laborder_repository_update_date() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
                BEGIN
                    IF TG_OP IN ('INSERT', 'UPDATE')
                    THEN
                        UPDATE laborder
                        SET repository_update_date = NOW()
                        WHERE
                            laborder.id = NEW.orderid;
                        RETURN NEW;
                    ELSIF TG_OP = 'DELETE'
                    THEN
                        UPDATE laborder
                        SET repository_update_date = NOW()
                        WHERE
                            laborder.id = OLD.orderid;
                        RETURN NEW;
                    END IF;
                END;
                $$;


ALTER FUNCTION "extract".trigger_fnc_set_laborder_repository_update_date() OWNER TO ukrdc;

--
-- TOC entry 299 (class 1255 OID 5836969)
-- Name: trigger_fnc_set_update_date(); Type: FUNCTION; Schema: extract; Owner: ukrdc
--

CREATE FUNCTION "extract".trigger_fnc_set_update_date() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
                BEGIN
                  NEW.update_date = NOW();
                  RETURN NEW;
                END;
                $$;


ALTER FUNCTION "extract".trigger_fnc_set_update_date() OWNER TO ukrdc;

SET default_tablespace = '';

--
-- TOC entry 192 (class 1259 OID 4791983)
-- Name: address; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".address (
    id character varying(100) NOT NULL,
    pid character varying(30) NOT NULL,
    idx integer,
    addressuse character varying(10),
    fromtime date,
    totime date,
    street character varying(100),
    town character varying(100),
    county character varying(100),
    postcode character varying(10),
    countrycode character varying(100),
    countrycodestd character varying(100),
    countrydesc character varying(100),
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone
);


ALTER TABLE "extract".address OWNER TO ukrdc;

--
-- TOC entry 193 (class 1259 OID 4791989)
-- Name: allergy; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".allergy (
    id character varying(100) NOT NULL,
    pid character varying(30) NOT NULL,
    idx integer,
    allergycode character varying(100),
    allergycodestd character varying(100),
    allergydesc character varying(100),
    allergycategorycode character varying(100),
    allergycategorycodestd character varying(100),
    allergycategorydesc character varying(100),
    severitycode character varying(100),
    severitycodestd character varying(100),
    severitydesc character varying(100),
    cliniciancode character varying(100),
    cliniciancodestd character varying(100),
    cliniciandesc character varying(100),
    discoverytime timestamp without time zone,
    confirmedtime timestamp without time zone,
    commenttext character varying(500),
    inactivetime timestamp without time zone,
    freetextallergy character varying(500),
    qualifyingdetails character varying(500),
    updatedon timestamp without time zone,
    actioncode character varying(3),
    externalid character varying(100),
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone
);


ALTER TABLE "extract".allergy OWNER TO ukrdc;

--
-- TOC entry 194 (class 1259 OID 4791995)
-- Name: causeofdeath; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".causeofdeath (
    pid character varying(30) NOT NULL,
    diagnosistype character varying(50),
    diagnosingcliniciancode character varying(100),
    diagnosingcliniciancodestd character varying(100),
    diagnosingcliniciandesc character varying(100),
    diagnosiscode character varying(100),
    diagnosiscodestd character varying(100),
    diagnosisdesc character varying(255),
    comments text,
    enteredon timestamp without time zone,
    updatedon timestamp without time zone,
    actioncode character varying(3),
    externalid character varying(100),
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone
);


ALTER TABLE "extract".causeofdeath OWNER TO ukrdc;

--
-- TOC entry 195 (class 1259 OID 4792001)
-- Name: clinicalrelationship; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".clinicalrelationship (
    id character varying(100) NOT NULL,
    pid character varying(30) NOT NULL,
    idx integer,
    cliniciancode character varying(100),
    cliniciancodestd character varying(100),
    cliniciandesc character varying(100),
    facilitycode character varying(100),
    facilitycodestd character varying(100),
    facilitydesc character varying(100),
    fromtime date,
    totime date,
    updatedon timestamp without time zone,
    actioncode character varying(3),
    externalid character varying(100),
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone
);


ALTER TABLE "extract".clinicalrelationship OWNER TO ukrdc;

--
-- TOC entry 250 (class 1259 OID 16525241)
-- Name: code_exclusion; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".code_exclusion (
    coding_standard character varying NOT NULL,
    code character varying NOT NULL,
    system character varying NOT NULL
);


ALTER TABLE "extract".code_exclusion OWNER TO ukrdc;

--
-- TOC entry 196 (class 1259 OID 4792007)
-- Name: code_list; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".code_list (
    coding_standard character varying(256) NOT NULL,
    code character varying(256) NOT NULL,
    description character varying(256),
    object_type character varying(256),
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone,
    units character varying(256)
);


ALTER TABLE "extract".code_list OWNER TO ukrdc;

--
-- TOC entry 197 (class 1259 OID 4792013)
-- Name: code_map; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".code_map (
    source_coding_standard character varying(256) NOT NULL,
    source_code character varying(256) NOT NULL,
    destination_coding_standard character varying(256) NOT NULL,
    destination_code character varying(256) NOT NULL,
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone
);


ALTER TABLE "extract".code_map OWNER TO ukrdc;

--
-- TOC entry 198 (class 1259 OID 4792019)
-- Name: contactdetail; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".contactdetail (
    id character varying(100) NOT NULL,
    pid character varying(30) NOT NULL,
    idx integer,
    contactuse character varying(10),
    contactvalue character varying(100),
    commenttext character varying(100),
    updatedon timestamp without time zone,
    actioncode character varying(3),
    externalid character varying(100),
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone
);


ALTER TABLE "extract".contactdetail OWNER TO ukrdc;

--
-- TOC entry 199 (class 1259 OID 4792022)
-- Name: diagnosis; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".diagnosis (
    id character varying(100) NOT NULL,
    pid character varying(30) NOT NULL,
    idx integer,
    diagnosistype character varying(50),
    diagnosingcliniciancode character varying(100),
    diagnosingcliniciancodestd character varying(100),
    diagnosingcliniciandesc character varying(100),
    diagnosiscode character varying(100),
    diagnosiscodestd character varying(100),
    diagnosisdesc character varying(255),
    comments text,
    identificationtime timestamp without time zone,
    onsettime timestamp without time zone,
    enteredon timestamp without time zone,
    updatedon timestamp without time zone,
    actioncode character varying(3),
    externalid character varying(100),
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone,
    enteredatcode character varying(100),
    enteredatcodestd character varying(100),
    enteredatdesc character varying(100),
    encounternumber character varying(100),
    verificationstatus character varying(100)
);


ALTER TABLE "extract".diagnosis OWNER TO ukrdc;

--
-- TOC entry 200 (class 1259 OID 4792028)
-- Name: dialysissession; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".dialysissession (
    id character varying(100) NOT NULL,
    pid character varying(30) NOT NULL,
    idx integer,
    proceduretypecode character varying(100),
    proceduretypecodestd character varying(100),
    proceduretypedesc character varying(100),
    cliniciancode character varying(100),
    cliniciancodestd character varying(100),
    cliniciandesc character varying(100),
    proceduretime timestamp without time zone,
    enteredbycode character varying(100),
    enteredbycodestd character varying(100),
    enteredbydesc character varying(100),
    enteredatcode character varying(100),
    enteredatcodestd character varying(100),
    enteredatdesc character varying(100),
    qhd19 character varying(255),
    qhd20 character varying(255),
    qhd21 character varying(255),
    qhd22 character varying(255),
    qhd30 character varying(255),
    qhd31 character varying(255),
    qhd32 character varying(255),
    qhd33 character varying(255),
    updatedon timestamp without time zone,
    actioncode character varying(3),
    externalid character varying(100),
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone
);


ALTER TABLE "extract".dialysissession OWNER TO ukrdc;

--
-- TOC entry 201 (class 1259 OID 4792034)
-- Name: document; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".document (
    id character varying(100) NOT NULL,
    pid character varying(30) NOT NULL,
    idx integer,
    documenttime timestamp without time zone,
    notetext text,
    documenttypecode character varying(100),
    documenttypecodestd character varying(100),
    documenttypedesc character varying(100),
    cliniciancode character varying(100),
    cliniciancodestd character varying(100),
    cliniciandesc character varying(100),
    documentname character varying(100),
    statuscode character varying(100),
    statuscodestd character varying(100),
    statusdesc character varying(100),
    enteredbycode character varying(100),
    enteredbycodestd character varying(100),
    enteredbydesc character varying(100),
    enteredatcode character varying(100),
    enteredatcodestd character varying(100),
    enteredatdesc character varying(100),
    filetype character varying(100),
    filename character varying(100),
    stream bytea,
    documenturl character varying(100),
    repositoryupdatedate timestamp without time zone NOT NULL,
    updatedon timestamp without time zone,
    actioncode character varying(3),
    externalid character varying(100),
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone
);


ALTER TABLE "extract".document OWNER TO ukrdc;

--
-- TOC entry 202 (class 1259 OID 4792040)
-- Name: encounter; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".encounter (
    id character varying(100) NOT NULL,
    pid character varying(30) NOT NULL,
    idx integer,
    encounternumber character varying(100),
    encountertype character varying(100),
    fromtime timestamp without time zone,
    totime timestamp without time zone,
    admittingcliniciancode character varying(100),
    admittingcliniciancodestd character varying(100),
    admittingcliniciandesc character varying(100),
    admitreasoncode character varying(100),
    admitreasoncodestd character varying(100),
    admitreasondesc character varying(100),
    admissionsourcecode character varying(100),
    admissionsourcecodestd character varying(100),
    admissionsourcedesc character varying(100),
    dischargereasoncode character varying(100),
    dischargereasoncodestd character varying(100),
    dischargereasondesc character varying(100),
    dischargelocationcode character varying(100),
    dischargelocationcodestd character varying(100),
    dischargelocationdesc character varying(100),
    healthcarefacilitycode character varying(100),
    healthcarefacilitycodestd character varying(100),
    healthcarefacilitydesc character varying(100),
    enteredatcode character varying(100),
    enteredatcodestd character varying(100),
    enteredatdesc character varying(100),
    visitdescription character varying(100),
    updatedon timestamp without time zone,
    actioncode character varying(3),
    externalid character varying(100),
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone
);


ALTER TABLE "extract".encounter OWNER TO ukrdc;

--
-- TOC entry 203 (class 1259 OID 4792046)
-- Name: eventcontrol; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".eventcontrol (
    eventtype character(20) NOT NULL,
    eventdate timestamp without time zone NOT NULL,
    pendingeventdate timestamp without time zone,
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone
);


ALTER TABLE "extract".eventcontrol OWNER TO ukrdc;

--
-- TOC entry 239 (class 1259 OID 14070597)
-- Name: facility; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".facility (
    code character varying(256) NOT NULL,
    pkb_out boolean DEFAULT false,
    pkb_in boolean DEFAULT false,
    pkb_msg_exclusions text[],
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone
);


ALTER TABLE "extract".facility OWNER TO ukrdc;

--
-- TOC entry 204 (class 1259 OID 4792049)
-- Name: familydoctor; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".familydoctor (
    id character varying(100) NOT NULL,
    gpname character varying(100),
    gpid character varying(20),
    gppracticeid character varying(20),
    addressuse character varying(10),
    fromtime date,
    totime date,
    street character varying(100),
    town character varying(100),
    county character varying(100),
    postcode character varying(10),
    countrycode character varying(100),
    countrycodestd character varying(100),
    countrydesc character varying(100),
    contactuse character varying(10),
    contactvalue character varying(100),
    email character varying(100),
    commenttext character varying(100),
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone
);


ALTER TABLE "extract".familydoctor OWNER TO ukrdc;

--
-- TOC entry 205 (class 1259 OID 4792055)
-- Name: familyhistory; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".familyhistory (
    id character varying(100) NOT NULL,
    pid character varying(30) NOT NULL,
    idx integer,
    familymembercode character varying(100),
    familymembercodestd character varying(100),
    familymemberdesc character varying(100),
    diagnosiscode character varying(100),
    diagnosiscodestd character varying(100),
    diagnosisdesc character varying(100),
    notetext character varying(100),
    enteredatcode character varying(100),
    enteredatcodestd character varying(100),
    enteredatdesc character varying(100),
    fromtime timestamp without time zone,
    totime timestamp without time zone,
    updatedon timestamp without time zone,
    actioncode character varying(3),
    externalid character varying(100),
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone
);


ALTER TABLE "extract".familyhistory OWNER TO ukrdc;

--
-- TOC entry 206 (class 1259 OID 4792061)
-- Name: laborder; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".laborder (
    id character varying(100) NOT NULL,
    pid character varying(30) NOT NULL,
    placerid character varying(100),
    fillerid character varying(100),
    receivinglocationcode character varying(100),
    receivinglocationcodestd character varying(100),
    receivinglocationdesc character varying(100),
    orderedbycode character varying(100),
    orderedbycodestd character varying(100),
    orderedbydesc character varying(100),
    orderitemcode character varying(100),
    orderitemcodestd character varying(100),
    orderitemdesc character varying(100),
    prioritycode character varying(100),
    prioritycodestd character varying(100),
    prioritydesc character varying(100),
    status character varying(100),
    ordercategorycode character varying(100),
    ordercategorycodestd character varying(100),
    ordercategorydesc character varying(100),
    specimensource character varying(50),
    specimenreceivedtime timestamp without time zone,
    specimencollectedtime timestamp without time zone,
    duration character varying(50),
    patientclasscode character varying(100),
    patientclasscodestd character varying(100),
    patientclassdesc character varying(100),
    enteredon timestamp without time zone,
    enteredatcode character varying(100),
    enteredatcodestd character varying(100),
    enteredatdesc character varying(100),
    enteringorganizationcode character varying(100),
    enteringorganizationcodestd character varying(100),
    enteringorganizationdesc character varying(100),
    updatedon timestamp without time zone,
    actioncode character varying(3),
    externalid character varying(100),
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone,
    repository_update_date timestamp without time zone
);


ALTER TABLE "extract".laborder OWNER TO ukrdc;

--
-- TOC entry 207 (class 1259 OID 4792067)
-- Name: level; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".level (
    id character varying(100) NOT NULL,
    surveyid character varying(100) NOT NULL,
    idx integer,
    levelvalue character varying(100),
    leveltypecode character varying(100),
    leveltypecodestd character varying(100),
    leveltypedesc character varying(100),
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone
);


ALTER TABLE "extract".level OWNER TO ukrdc;

--
-- TOC entry 208 (class 1259 OID 4792073)
-- Name: medication; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".medication (
    id character varying(150) NOT NULL,
    pid character varying(30) NOT NULL,
    idx integer,
    prescriptionnumber character varying(100),
    fromtime timestamp without time zone,
    totime timestamp without time zone,
    orderedbycode character varying(100),
    orderedbycodestd character varying(100),
    orderedbydesc character varying(100),
    enteringorganizationcode character varying(100),
    enteringorganizationcodestd character varying(100),
    enteringorganizationdesc character varying(100),
    routecode character varying(10),
    routecodestd character varying(100),
    routedesc character varying(100),
    drugproductidcode character varying(100),
    drugproductidcodestd character varying(100),
    drugproductiddesc character varying(100),
    drugproductgeneric character varying(255),
    drugproductlabelname character varying(255),
    drugproductformcode character varying(100),
    drugproductformcodestd character varying(100),
    drugproductformdesc character varying(100),
    drugproductstrengthunitscode character varying(100),
    drugproductstrengthunitscodestd character varying(100),
    drugproductstrengthunitsdesc character varying(100),
    frequency character varying(255),
    commenttext character varying(1000),
    dosequantity numeric(19,2),
    doseuomcode character varying(100),
    doseuomcodestd character varying(100),
    doseuomdesc character varying(100),
    indication character varying(100),
    repositoryupdatedate timestamp without time zone NOT NULL,
    updatedon timestamp without time zone,
    actioncode character varying(3),
    externalid character varying(100),
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone,
    encounternumber character varying(100)
);


ALTER TABLE "extract".medication OWNER TO ukrdc;

--
-- TOC entry 209 (class 1259 OID 4792079)
-- Name: name; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".name (
    id character varying(100) NOT NULL,
    pid character varying(30) NOT NULL,
    idx integer,
    nameuse character varying(10),
    prefix character varying(10),
    family character varying(60),
    given character varying(60),
    othergivennames character varying(60),
    suffix character varying(10),
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone
);


ALTER TABLE "extract".name OWNER TO ukrdc;

--
-- TOC entry 210 (class 1259 OID 4792082)
-- Name: observation; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".observation (
    id character varying(100) NOT NULL,
    pid character varying(30) NOT NULL,
    idx integer,
    observationtime timestamp without time zone,
    observationcode character varying(100),
    observationcodestd character varying(100),
    observationdesc character varying(100),
    observationvalue character varying(100),
    observationunits character varying(100),
    prepost character varying(4),
    commenttext character varying(100),
    cliniciancode character varying(100),
    cliniciancodestd character varying(100),
    cliniciandesc character varying(100),
    enteredatcode character varying(100),
    enteredatcodestd character varying(100),
    enteredatdesc character varying(100),
    enteringorganizationcode character varying(100),
    enteringorganizationcodestd character varying(100),
    enteringorganizationdesc character varying(100),
    updatedon timestamp without time zone,
    actioncode character varying(3),
    externalid character varying(100),
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone
);


ALTER TABLE "extract".observation OWNER TO ukrdc;

--
-- TOC entry 211 (class 1259 OID 4792088)
-- Name: optout; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".optout (
    id character varying(100) NOT NULL,
    pid character varying(30) NOT NULL,
    idx integer,
    programname character varying(100),
    programdescription character varying(100),
    enteredbycode character varying(100),
    enteredbycodestd character varying(100),
    enteredbydesc character varying(100),
    enteredatcode character varying(100),
    enteredatcodestd character varying(100),
    enteredatdesc character varying(100),
    fromtime date,
    totime date,
    updatedon timestamp without time zone,
    actioncode character varying(3),
    externalid character varying(100),
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone
);


ALTER TABLE "extract".optout OWNER TO ukrdc;

--
-- TOC entry 212 (class 1259 OID 4792094)
-- Name: patient; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".patient (
    pid character varying(30) NOT NULL,
    birthtime timestamp without time zone,
    deathtime timestamp without time zone,
    gender character varying(2),
    countryofbirth character varying(3),
    ethnicgroupcode character varying(100),
    ethnicgroupcodestd character varying(100),
    ethnicgroupdesc character varying(100),
    occupationcode character varying(100),
    occupationcodestd character varying(100),
    occupationdesc character varying(100),
    primarylanguagecode character varying(100),
    primarylanguagecodestd character varying(100),
    primarylanguagedesc character varying(100),
    death boolean,
    persontocontactname character varying(100),
    persontocontact_relationship character varying(20),
    persontocontact_contactnumber character varying(20),
    persontocontact_contactnumbertype character varying(20),
    persontocontact_contactnumbercomments character varying(200),
    updatedon timestamp without time zone,
    actioncode character varying(3),
    externalid character varying(100),
    bloodgroup character varying(100),
    bloodrhesus character varying(100),
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone
);


ALTER TABLE "extract".patient OWNER TO ukrdc;

--
-- TOC entry 213 (class 1259 OID 4792100)
-- Name: patientnumber; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".patientnumber (
    id character varying(100) NOT NULL,
    pid character varying(30) NOT NULL,
    idx integer,
    patientid character varying(50),
    numbertype character varying(3),
    organization character varying(50),
    updatedon timestamp without time zone,
    actioncode character varying(3),
    externalid character varying(100),
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone
);


ALTER TABLE "extract".patientnumber OWNER TO ukrdc;

--
-- TOC entry 214 (class 1259 OID 4792103)
-- Name: patientrecord; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".patientrecord (
    pid character varying(30) NOT NULL,
    sendingfacility character varying(7) NOT NULL,
    sendingextract character varying(6) NOT NULL,
    localpatientid character varying(17) NOT NULL,
    ukrdcid character varying(10),
    channelname character varying(50),
    channelid character varying(50),
    extracttime character varying(50),
    repositorycreationdate timestamp without time zone NOT NULL,
    repositoryupdatedate timestamp without time zone NOT NULL,
    startdate timestamp without time zone,
    stopdate timestamp without time zone,
    migrated boolean DEFAULT false NOT NULL,
    schemaversion character varying(50),
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone
);


ALTER TABLE "extract".patientrecord OWNER TO ukrdc;

--
-- TOC entry 249 (class 1259 OID 16081062)
-- Name: pkb_links; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".pkb_links (
    id integer NOT NULL,
    link character varying,
    link_name character varying,
    coding_standard character varying,
    code character varying
);


ALTER TABLE "extract".pkb_links OWNER TO ukrdc;

--
-- TOC entry 248 (class 1259 OID 16081060)
-- Name: pkb_links_id_seq; Type: SEQUENCE; Schema: extract; Owner: ukrdc
--

CREATE SEQUENCE "extract".pkb_links_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "extract".pkb_links_id_seq OWNER TO ukrdc;

--
-- TOC entry 3544 (class 0 OID 0)
-- Dependencies: 248
-- Name: pkb_links_id_seq; Type: SEQUENCE OWNED BY; Schema: extract; Owner: ukrdc
--

ALTER SEQUENCE "extract".pkb_links_id_seq OWNED BY "extract".pkb_links.id;


--
-- TOC entry 215 (class 1259 OID 4792107)
-- Name: procedure; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".procedure (
    id character varying(100) NOT NULL,
    pid character varying(30) NOT NULL,
    idx integer,
    proceduretypecode character varying(100),
    proceduretypecodestd character varying(100),
    proceduretypedesc character varying(100),
    cliniciancode character varying(100),
    cliniciancodestd character varying(100),
    cliniciandesc character varying(100),
    proceduretime timestamp without time zone,
    enteredbycode character varying(100),
    enteredbycodestd character varying(100),
    enteredbydesc character varying(100),
    enteredatcode character varying(100),
    enteredatcodestd character varying(100),
    enteredatdesc character varying(100),
    updatedon timestamp without time zone,
    actioncode character varying(3),
    externalid character varying(100),
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone
);


ALTER TABLE "extract".procedure OWNER TO ukrdc;

--
-- TOC entry 216 (class 1259 OID 4792113)
-- Name: programmembership; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".programmembership (
    id character varying(100) NOT NULL,
    pid character varying(30) NOT NULL,
    programname character varying(100),
    programdescription character varying(100),
    enteredbycode character varying(100),
    enteredbycodestd character varying(100),
    enteredbydesc character varying(100),
    enteredatcode character varying(100),
    enteredatcodestd character varying(100),
    enteredatdesc character varying(100),
    fromtime date,
    totime date,
    updatedon timestamp without time zone,
    actioncode character varying(3),
    externalid character varying(100),
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone
);


ALTER TABLE "extract".programmembership OWNER TO ukrdc;

--
-- TOC entry 217 (class 1259 OID 4792119)
-- Name: pvdata; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".pvdata (
    id character varying(100) NOT NULL,
    rrtstatus character varying(100),
    tpstatus character varying(100),
    diagnosisdate date,
    bloodgroup character varying(10),
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone
);


ALTER TABLE "extract".pvdata OWNER TO ukrdc;

--
-- TOC entry 218 (class 1259 OID 4792122)
-- Name: pvdelete; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".pvdelete (
    did integer NOT NULL,
    pid character varying(30) NOT NULL,
    observationtime timestamp without time zone,
    serviceidcode character varying(100),
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone
);


ALTER TABLE "extract".pvdelete OWNER TO ukrdc;

--
-- TOC entry 219 (class 1259 OID 4792125)
-- Name: pvdelete_did_seq; Type: SEQUENCE; Schema: extract; Owner: ukrdc
--

CREATE SEQUENCE "extract".pvdelete_did_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "extract".pvdelete_did_seq OWNER TO ukrdc;

--
-- TOC entry 3550 (class 0 OID 0)
-- Dependencies: 219
-- Name: pvdelete_did_seq; Type: SEQUENCE OWNED BY; Schema: extract; Owner: ukrdc
--

ALTER SEQUENCE "extract".pvdelete_did_seq OWNED BY "extract".pvdelete.did;


--
-- TOC entry 220 (class 1259 OID 4792127)
-- Name: question; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".question (
    id character varying(100) NOT NULL,
    surveyid character varying(100) NOT NULL,
    idx integer,
    questiontypecode character varying(100),
    questiontypecodestd character varying(100),
    questiontypedesc character varying(100),
    response character varying(100),
    questiontext character varying(100),
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone
);


ALTER TABLE "extract".question OWNER TO ukrdc;

--
-- TOC entry 221 (class 1259 OID 4792133)
-- Name: renaldiagnosis; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".renaldiagnosis (
    pid character varying(30) NOT NULL,
    diagnosistype character varying(50),
    diagnosingcliniciancode character varying(100),
    diagnosingcliniciancodestd character varying(100),
    diagnosingcliniciandesc character varying(100),
    diagnosiscode character varying(100),
    diagnosiscodestd character varying(100),
    diagnosisdesc character varying(255),
    comments text,
    identificationtime timestamp without time zone,
    onsettime timestamp without time zone,
    enteredon timestamp without time zone,
    updatedon timestamp without time zone,
    actioncode character varying(3),
    externalid character varying(100),
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone
);


ALTER TABLE "extract".renaldiagnosis OWNER TO ukrdc;

--
-- TOC entry 222 (class 1259 OID 4792139)
-- Name: resultitem; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".resultitem (
    id character varying(100) NOT NULL,
    orderid character varying(100) NOT NULL,
    resulttype character varying(2),
    serviceidcode character varying(100),
    serviceidcodestd character varying(100),
    serviceiddesc character varying(100),
    subid character varying(50),
    resultvalue character varying(20),
    resultvalueunits character varying(30),
    referencerange character varying(30),
    interpretationcodes character varying(50),
    status character varying(5),
    observationtime timestamp without time zone,
    commenttext character varying(1000),
    referencecomment character varying(1000),
    prepost character varying(4),
    enteredon timestamp without time zone,
    updatedon timestamp without time zone,
    actioncode character varying(3),
    externalid character varying(100),
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone
);


ALTER TABLE "extract".resultitem OWNER TO ukrdc;

--
-- TOC entry 223 (class 1259 OID 4792145)
-- Name: satellite_map; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".satellite_map (
    satellite_code character varying(10) NOT NULL,
    main_unit_code character varying(10) NOT NULL,
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone
);


ALTER TABLE "extract".satellite_map OWNER TO ukrdc;

--
-- TOC entry 224 (class 1259 OID 4792148)
-- Name: score; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".score (
    id character varying(100) NOT NULL,
    surveyid character varying(100) NOT NULL,
    idx integer,
    scorevalue character varying(100),
    scoretypecode character varying(100),
    scoretypecodestd character varying(100),
    scoretypedesc character varying(100),
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone
);


ALTER TABLE "extract".score OWNER TO ukrdc;

--
-- TOC entry 225 (class 1259 OID 4792154)
-- Name: socialhistory; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".socialhistory (
    id character varying(100) NOT NULL,
    pid character varying(30) NOT NULL,
    idx integer,
    socialhabitcode character varying(100),
    socialhabitcodestd character varying(100),
    socialhabitdesc character varying(100),
    updatedon timestamp without time zone,
    actioncode character varying(3),
    externalid character varying(100),
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone
);


ALTER TABLE "extract".socialhistory OWNER TO ukrdc;

--
-- TOC entry 226 (class 1259 OID 4792160)
-- Name: survey; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".survey (
    id character varying(100) NOT NULL,
    pid character varying(30) NOT NULL,
    surveytime timestamp without time zone NOT NULL,
    surveytypecode character varying(100),
    surveytypecodestd character varying(100),
    surveytypedesc character varying(100),
    typeoftreatment character varying(100),
    hdlocation character varying(100),
    template character varying(100),
    enteredbycode character varying(100),
    enteredbycodestd character varying(100),
    enteredbydesc character varying(100),
    enteredatcode character varying(100),
    enteredatcodestd character varying(100),
    enteredatdesc character varying(100),
    updatedon timestamp without time zone,
    actioncode character varying(3),
    externalid character varying(100),
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone
);


ALTER TABLE "extract".survey OWNER TO ukrdc;

--
-- TOC entry 227 (class 1259 OID 4792166)
-- Name: transplant; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".transplant (
    id character varying(100) NOT NULL,
    pid character varying(30) NOT NULL,
    idx integer,
    proceduretypecode character varying(100),
    proceduretypecodestd character varying(100),
    proceduretypedesc character varying(100),
    cliniciancode character varying(100),
    cliniciancodestd character varying(100),
    cliniciandesc character varying(100),
    proceduretime timestamp without time zone,
    enteredbycode character varying(100),
    enteredbycodestd character varying(100),
    enteredbydesc character varying(100),
    enteredatcode character varying(100),
    enteredatcodestd character varying(100),
    enteredatdesc character varying(100),
    updatedon timestamp without time zone,
    actioncode character varying(3),
    externalid character varying(100),
    tra64 timestamp without time zone,
    tra65 character varying(255),
    tra66 character varying(255),
    tra69 timestamp without time zone,
    tra76 character varying(255),
    tra77 character varying(255),
    tra78 character varying(255),
    tra79 character varying(255),
    tra80 character varying(255),
    tra8a character varying(255),
    tra81 character varying(255),
    tra82 character varying(255),
    tra83 character varying(255),
    tra84 character varying(255),
    tra85 character varying(255),
    tra86 character varying(255),
    tra87 character varying(255),
    tra88 character varying(255),
    tra89 character varying(255),
    tra90 character varying(255),
    tra91 character varying(255),
    tra92 character varying(255),
    tra93 character varying(255),
    tra94 character varying(255),
    tra95 character varying(255),
    tra96 character varying(255),
    tra97 character varying(255),
    tra98 character varying(255),
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone
);


ALTER TABLE "extract".transplant OWNER TO ukrdc;

--
-- TOC entry 228 (class 1259 OID 4792172)
-- Name: transplantlist; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".transplantlist (
    id character varying(100) NOT NULL,
    pid character varying(30) NOT NULL,
    idx integer,
    encounternumber character varying(100),
    encountertype character varying(100),
    fromtime timestamp without time zone,
    totime timestamp without time zone,
    admittingcliniciancode character varying(100),
    admittingcliniciancodestd character varying(100),
    admittingcliniciandesc character varying(100),
    admitreasoncode character varying(100),
    admitreasoncodestd character varying(100),
    admitreasondesc character varying(100),
    admissionsourcecode character varying(100),
    admissionsourcecodestd character varying(100),
    admissionsourcedesc character varying(100),
    dischargereasoncode character varying(100),
    dischargereasoncodestd character varying(100),
    dischargereasondesc character varying(100),
    dischargelocationcode character varying(100),
    dischargelocationcodestd character varying(100),
    dischargelocationdesc character varying(100),
    healthcarefacilitycode character varying(100),
    healthcarefacilitycodestd character varying(100),
    healthcarefacilitydesc character varying(100),
    enteredatcode character varying(100),
    enteredatcodestd character varying(100),
    enteredatdesc character varying(100),
    visitdescription character varying(100),
    updatedon timestamp without time zone,
    actioncode character varying(3),
    externalid character varying(100),
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone
);


ALTER TABLE "extract".transplantlist OWNER TO ukrdc;

--
-- TOC entry 229 (class 1259 OID 4792178)
-- Name: treatment; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".treatment (
    id character varying(100) NOT NULL,
    pid character varying(30) NOT NULL,
    idx integer,
    encounternumber character varying(100),
    encountertype character varying(100),
    fromtime timestamp without time zone,
    totime timestamp without time zone,
    admittingcliniciancode character varying(100),
    admittingcliniciancodestd character varying(100),
    admittingcliniciandesc character varying(100),
    admitreasoncode character varying(100),
    admitreasoncodestd character varying(100),
    admitreasondesc character varying(100),
    admissionsourcecode character varying(100),
    admissionsourcecodestd character varying(100),
    admissionsourcedesc character varying(100),
    dischargereasoncode character varying(100),
    dischargereasoncodestd character varying(100),
    dischargereasondesc character varying(100),
    dischargelocationcode character varying(100),
    dischargelocationcodestd character varying(100),
    dischargelocationdesc character varying(100),
    healthcarefacilitycode character varying(100),
    healthcarefacilitycodestd character varying(100),
    healthcarefacilitydesc character varying(100),
    enteredatcode character varying(100),
    enteredatcodestd character varying(100),
    enteredatdesc character varying(100),
    visitdescription character varying(100),
    updatedon timestamp without time zone,
    actioncode character varying(3),
    externalid character varying(100),
    hdp01 character varying(255),
    hdp02 character varying(255),
    hdp03 character varying(255),
    hdp04 character varying(255),
    qbl05 character varying(255),
    qbl06 character varying(255),
    qbl07 character varying(255),
    erf61 character varying(255),
    pat35 character varying(255),
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone
);


ALTER TABLE "extract".treatment OWNER TO ukrdc;

--
-- TOC entry 230 (class 1259 OID 4792184)
-- Name: ukrdc_ods_gp_codes; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".ukrdc_ods_gp_codes (
    code character varying(8) NOT NULL,
    name character varying(50),
    address1 character varying(35),
    postcode character varying(8),
    phone character varying(12),
    type "extract".gp_type,
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone
);


ALTER TABLE "extract".ukrdc_ods_gp_codes OWNER TO ukrdc;

--
-- TOC entry 231 (class 1259 OID 4792187)
-- Name: validationerror; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".validationerror (
    vid integer NOT NULL,
    pid character varying(30) NOT NULL,
    updatedon timestamp without time zone,
    errortype integer NOT NULL,
    message character varying(200),
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone
);


ALTER TABLE "extract".validationerror OWNER TO ukrdc;

--
-- TOC entry 232 (class 1259 OID 4792190)
-- Name: validationerror_vid_seq; Type: SEQUENCE; Schema: extract; Owner: ukrdc
--

CREATE SEQUENCE "extract".validationerror_vid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "extract".validationerror_vid_seq OWNER TO ukrdc;

--
-- TOC entry 3564 (class 0 OID 0)
-- Dependencies: 232
-- Name: validationerror_vid_seq; Type: SEQUENCE OWNED BY; Schema: extract; Owner: ukrdc
--

ALTER SEQUENCE "extract".validationerror_vid_seq OWNED BY "extract".validationerror.vid;


--
-- TOC entry 233 (class 1259 OID 4792192)
-- Name: vascularaccess; Type: TABLE; Schema: extract; Owner: ukrdc
--

CREATE TABLE "extract".vascularaccess (
    id character varying(100) NOT NULL,
    pid character varying(30) NOT NULL,
    idx integer,
    proceduretypecode character varying(100),
    proceduretypecodestd character varying(100),
    proceduretypedesc character varying(100),
    cliniciancode character varying(100),
    cliniciancodestd character varying(100),
    cliniciandesc character varying(100),
    proceduretime timestamp without time zone,
    enteredbycode character varying(100),
    enteredbycodestd character varying(100),
    enteredbydesc character varying(100),
    enteredatcode character varying(100),
    enteredatcodestd character varying(100),
    enteredatdesc character varying(100),
    updatedon timestamp without time zone,
    actioncode character varying(3),
    externalid character varying(100),
    acc19 character varying(255),
    acc20 character varying(255),
    acc21 character varying(255),
    acc22 character varying(255),
    acc30 character varying(255),
    acc40 character varying(255),
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    update_date timestamp without time zone
);


ALTER TABLE "extract".vascularaccess OWNER TO ukrdc;

--
-- TOC entry 242 (class 1259 OID 15156471)
-- Name: vwe_pkb_members; Type: VIEW; Schema: extract; Owner: ukrdc
--

CREATE VIEW "extract".vwe_pkb_members AS
 SELECT DISTINCT pr.ukrdcid
   FROM ("extract".programmembership pm
     JOIN "extract".patientrecord pr ON (((pm.pid)::text = (pr.pid)::text)))
  WHERE (((pm.programname)::text ~~ 'PKB%'::text) AND (pm.totime IS NULL));


ALTER TABLE "extract".vwe_pkb_members OWNER TO ukrdc;

--
-- TOC entry 246 (class 1259 OID 15156489)
-- Name: vwe_extract_pkb_deceased; Type: VIEW; Schema: extract; Owner: ukrdc
--

CREATE VIEW "extract".vwe_extract_pkb_deceased AS
 SELECT DISTINCT pr.ukrdcid
   FROM ("extract".patientrecord pr
     JOIN "extract".vwe_pkb_members ON (((pr.ukrdcid)::text = (vwe_pkb_members.ukrdcid)::text)))
  WHERE ((pr.ukrdcid)::text IN ( SELECT a.ukrdcid
           FROM ("extract".patientrecord a
             JOIN "extract".patient b ON (((a.pid)::text = (b.pid)::text)))
          WHERE (b.deathtime IS NOT NULL)));


ALTER TABLE "extract".vwe_extract_pkb_deceased OWNER TO ukrdc;

--
-- TOC entry 241 (class 1259 OID 15156467)
-- Name: vwe_pkb_test_patients; Type: VIEW; Schema: extract; Owner: ukrdc
--

CREATE VIEW "extract".vwe_pkb_test_patients AS
 SELECT DISTINCT patientnumber.pid
   FROM "extract".patientnumber
  WHERE ((patientnumber.patientid)::text = ANY ((ARRAY['4802588151'::character varying, '4587392774'::character varying])::text[]));


ALTER TABLE "extract".vwe_pkb_test_patients OWNER TO ukrdc;

--
-- TOC entry 245 (class 1259 OID 15156485)
-- Name: vwe_extract_pkb_deceased_test; Type: VIEW; Schema: extract; Owner: ukrdc
--

CREATE VIEW "extract".vwe_extract_pkb_deceased_test AS
 SELECT DISTINCT pr.ukrdcid
   FROM "extract".patientrecord pr
  WHERE ((pr.pid)::text IN ( SELECT vwe_pkb_test_patients.pid
           FROM "extract".vwe_pkb_test_patients));


ALTER TABLE "extract".vwe_extract_pkb_deceased_test OWNER TO ukrdc;

--
-- TOC entry 240 (class 1259 OID 14715539)
-- Name: vwe_pv_members; Type: VIEW; Schema: extract; Owner: ukrdc
--

CREATE VIEW "extract".vwe_pv_members AS
 SELECT DISTINCT pr.ukrdcid
   FROM ("extract".programmembership pm
     JOIN "extract".patientrecord pr ON (((pm.pid)::text = (pr.pid)::text)))
  WHERE (((pm.programname)::text ~~ 'PV.%'::text) AND (pm.totime IS NULL));


ALTER TABLE "extract".vwe_pv_members OWNER TO ukrdc;

--
-- TOC entry 244 (class 1259 OID 15156480)
-- Name: vwe_extract_pkb_new; Type: VIEW; Schema: extract; Owner: ukrdc
--

CREATE VIEW "extract".vwe_extract_pkb_new AS
 SELECT DISTINCT pr.ukrdcid
   FROM "extract".patientrecord pr
  WHERE ((NOT ((pr.ukrdcid)::text IN ( SELECT vwe_pkb_members.ukrdcid
           FROM "extract".vwe_pkb_members))) AND ((pr.ukrdcid)::text IN ( SELECT vwe_pv_members.ukrdcid
           FROM "extract".vwe_pv_members)) AND (NOT ((pr.ukrdcid)::text IN ( SELECT a.ukrdcid
           FROM ("extract".patientrecord a
             JOIN "extract".patient b ON (((a.pid)::text = (b.pid)::text)))
          WHERE (b.deathtime IS NOT NULL)))));


ALTER TABLE "extract".vwe_extract_pkb_new OWNER TO ukrdc;

--
-- TOC entry 243 (class 1259 OID 15156476)
-- Name: vwe_extract_pkb_new_test; Type: VIEW; Schema: extract; Owner: ukrdc
--

CREATE VIEW "extract".vwe_extract_pkb_new_test AS
 SELECT DISTINCT pr.ukrdcid
   FROM "extract".patientrecord pr
  WHERE ((pr.pid)::text IN ( SELECT vwe_pkb_test_patients.pid
           FROM "extract".vwe_pkb_test_patients));


ALTER TABLE "extract".vwe_extract_pkb_new_test OWNER TO ukrdc;

--
-- TOC entry 247 (class 1259 OID 15156576)
-- Name: vwe_extract_pkb_updates; Type: VIEW; Schema: extract; Owner: ukrdc
--

CREATE VIEW "extract".vwe_extract_pkb_updates AS
 SELECT patientrecord.pid,
    NULL::text AS id,
    'ADT_A28'::text AS msg_type
   FROM (("extract".patientrecord
     JOIN "extract".vwe_pkb_members ON (((patientrecord.ukrdcid)::text = (vwe_pkb_members.ukrdcid)::text)))
     JOIN "extract".facility ON (((patientrecord.sendingfacility)::text = (facility.code)::text)))
  WHERE ((facility.pkb_out = true) AND ((patientrecord.sendingextract)::text = ANY ((ARRAY['PV'::character varying, 'UKRDC'::character varying])::text[])) AND (((patientrecord.update_date IS NULL) AND (patientrecord.creation_date > ( SELECT eventcontrol.eventdate
           FROM "extract".eventcontrol
          WHERE (eventcontrol.eventtype = 'PKBEXTRACT'::bpchar)))) OR (EXISTS ( SELECT medication.id
           FROM "extract".medication
          WHERE (((medication.pid)::text = (patientrecord.pid)::text) AND (((medication.update_date IS NULL) AND (medication.creation_date > ( SELECT eventcontrol.eventdate
                   FROM "extract".eventcontrol
                  WHERE (eventcontrol.eventtype = 'PKBEXTRACT'::bpchar)))) OR ((medication.update_date IS NOT NULL) AND (medication.update_date > ( SELECT eventcontrol.eventdate
                   FROM "extract".eventcontrol
                  WHERE (eventcontrol.eventtype = 'PKBEXTRACT'::bpchar)))))))) OR (EXISTS ( SELECT diagnosis.id
           FROM "extract".diagnosis
          WHERE (((diagnosis.pid)::text = (patientrecord.pid)::text) AND (((diagnosis.update_date IS NULL) AND (diagnosis.creation_date > ( SELECT eventcontrol.eventdate
                   FROM "extract".eventcontrol
                  WHERE (eventcontrol.eventtype = 'PKBEXTRACT'::bpchar)))) OR ((diagnosis.update_date IS NOT NULL) AND (diagnosis.update_date > ( SELECT eventcontrol.eventdate
                   FROM "extract".eventcontrol
                  WHERE (eventcontrol.eventtype = 'PKBEXTRACT'::bpchar)))))))) OR (EXISTS ( SELECT renaldiagnosis.pid
           FROM "extract".renaldiagnosis
          WHERE (((renaldiagnosis.pid)::text = (patientrecord.pid)::text) AND (((renaldiagnosis.update_date IS NULL) AND (renaldiagnosis.creation_date > ( SELECT eventcontrol.eventdate
                   FROM "extract".eventcontrol
                  WHERE (eventcontrol.eventtype = 'PKBEXTRACT'::bpchar)))) OR ((renaldiagnosis.update_date IS NOT NULL) AND (renaldiagnosis.update_date > ( SELECT eventcontrol.eventdate
                   FROM "extract".eventcontrol
                  WHERE (eventcontrol.eventtype = 'PKBEXTRACT'::bpchar))))))))))
UNION ALL
 SELECT patientrecord.pid,
    NULL::text AS id,
    'MDM_T02_CP'::text AS msg_type
   FROM ((("extract".patientrecord
     LEFT JOIN "extract".pvdata ON (((patientrecord.pid)::text = (pvdata.id)::text)))
     JOIN "extract".vwe_pkb_members ON (((patientrecord.ukrdcid)::text = (vwe_pkb_members.ukrdcid)::text)))
     JOIN "extract".facility ON (((patientrecord.sendingfacility)::text = (facility.code)::text)))
  WHERE ((facility.pkb_out = true) AND ((patientrecord.sendingextract)::text = ANY ((ARRAY['PV'::character varying, 'UKRDC'::character varying])::text[])) AND (((pvdata.update_date IS NULL) AND (pvdata.creation_date > ( SELECT eventcontrol.eventdate
           FROM "extract".eventcontrol
          WHERE (eventcontrol.eventtype = 'PKBEXTRACT'::bpchar)))) OR ((pvdata.update_date IS NOT NULL) AND (pvdata.update_date > ( SELECT eventcontrol.eventdate
           FROM "extract".eventcontrol
          WHERE (eventcontrol.eventtype = 'PKBEXTRACT'::bpchar)))) OR (EXISTS ( SELECT diagnosis.id
           FROM "extract".diagnosis
          WHERE (((diagnosis.pid)::text = (patientrecord.pid)::text) AND (((diagnosis.update_date IS NULL) AND (diagnosis.creation_date > ( SELECT eventcontrol.eventdate
                   FROM "extract".eventcontrol
                  WHERE (eventcontrol.eventtype = 'PKBEXTRACT'::bpchar)))) OR ((diagnosis.update_date IS NOT NULL) AND (diagnosis.update_date > ( SELECT eventcontrol.eventdate
                   FROM "extract".eventcontrol
                  WHERE (eventcontrol.eventtype = 'PKBEXTRACT'::bpchar)))))))) OR (EXISTS ( SELECT renaldiagnosis.pid
           FROM "extract".renaldiagnosis
          WHERE (((renaldiagnosis.pid)::text = (patientrecord.pid)::text) AND (((renaldiagnosis.update_date IS NULL) AND (renaldiagnosis.creation_date > ( SELECT eventcontrol.eventdate
                   FROM "extract".eventcontrol
                  WHERE (eventcontrol.eventtype = 'PKBEXTRACT'::bpchar)))) OR ((renaldiagnosis.update_date IS NOT NULL) AND (renaldiagnosis.update_date > ( SELECT eventcontrol.eventdate
                   FROM "extract".eventcontrol
                  WHERE (eventcontrol.eventtype = 'PKBEXTRACT'::bpchar)))))))) OR (EXISTS ( SELECT a.id
           FROM ("extract".pvdata a
             JOIN "extract".patientrecord b ON (((a.id)::text = (b.pid)::text)))
          WHERE (((b.ukrdcid)::text = (patientrecord.ukrdcid)::text) AND ((b.sendingfacility)::text = 'NHSBT'::text) AND (((a.update_date IS NULL) AND (a.creation_date > ( SELECT eventcontrol.eventdate
                   FROM "extract".eventcontrol
                  WHERE (eventcontrol.eventtype = 'PKBEXTRACT'::bpchar)))) OR ((a.update_date IS NOT NULL) AND (a.update_date > ( SELECT eventcontrol.eventdate
                   FROM "extract".eventcontrol
                  WHERE (eventcontrol.eventtype = 'PKBEXTRACT'::bpchar))))))))))
UNION ALL
 SELECT document.pid,
    document.id,
    'MDM_T02_DOC'::text AS msg_type
   FROM ((("extract".document
     JOIN "extract".patientrecord ON (((document.pid)::text = (patientrecord.pid)::text)))
     JOIN "extract".vwe_pkb_members ON (((patientrecord.ukrdcid)::text = (vwe_pkb_members.ukrdcid)::text)))
     JOIN "extract".facility ON (((patientrecord.sendingfacility)::text = (facility.code)::text)))
  WHERE ((facility.pkb_out = true) AND ((patientrecord.sendingextract)::text = ANY ((ARRAY['PV'::character varying, 'UKRDC'::character varying])::text[])) AND (((document.update_date IS NULL) AND (document.creation_date > ( SELECT eventcontrol.eventdate
           FROM "extract".eventcontrol
          WHERE (eventcontrol.eventtype = 'PKBEXTRACT'::bpchar)))) OR ((document.update_date IS NOT NULL) AND (document.update_date > ( SELECT eventcontrol.eventdate
           FROM "extract".eventcontrol
          WHERE (eventcontrol.eventtype = 'PKBEXTRACT'::bpchar))))))
UNION ALL
 SELECT laborder.pid,
    laborder.id,
    'ORU_R01_LAB'::text AS msg_type
   FROM ((("extract".laborder
     JOIN "extract".patientrecord ON (((laborder.pid)::text = (patientrecord.pid)::text)))
     JOIN "extract".vwe_pkb_members ON (((patientrecord.ukrdcid)::text = (vwe_pkb_members.ukrdcid)::text)))
     JOIN "extract".facility ON (((patientrecord.sendingfacility)::text = (facility.code)::text)))
  WHERE ((facility.pkb_out = true) AND ((patientrecord.sendingextract)::text = ANY ((ARRAY['PV'::character varying, 'UKRDC'::character varying])::text[])) AND (((laborder.update_date IS NULL) AND (laborder.creation_date > ( SELECT eventcontrol.eventdate
           FROM "extract".eventcontrol
          WHERE (eventcontrol.eventtype = 'PKBEXTRACT'::bpchar)))) OR ((laborder.update_date IS NOT NULL) AND (laborder.update_date > ( SELECT eventcontrol.eventdate
           FROM "extract".eventcontrol
          WHERE (eventcontrol.eventtype = 'PKBEXTRACT'::bpchar)))) OR ((laborder.repository_update_date IS NOT NULL) AND (laborder.repository_update_date > ( SELECT eventcontrol.eventdate
           FROM "extract".eventcontrol
          WHERE (eventcontrol.eventtype = 'PKBEXTRACT'::bpchar))))))
UNION ALL
 SELECT observation.pid,
    observation.id,
    'ORU_R01_OBS'::text AS msg_type
   FROM ((("extract".observation
     JOIN "extract".patientrecord ON (((observation.pid)::text = (patientrecord.pid)::text)))
     JOIN "extract".vwe_pkb_members ON (((patientrecord.ukrdcid)::text = (vwe_pkb_members.ukrdcid)::text)))
     JOIN "extract".facility ON (((patientrecord.sendingfacility)::text = (facility.code)::text)))
  WHERE ((facility.pkb_out = true) AND ((patientrecord.sendingextract)::text = ANY ((ARRAY['PV'::character varying, 'UKRDC'::character varying])::text[])) AND (((observation.update_date IS NULL) AND (observation.creation_date > ( SELECT eventcontrol.eventdate
           FROM "extract".eventcontrol
          WHERE (eventcontrol.eventtype = 'PKBEXTRACT'::bpchar)))) OR ((observation.update_date IS NOT NULL) AND (observation.update_date > ( SELECT eventcontrol.eventdate
           FROM "extract".eventcontrol
          WHERE (eventcontrol.eventtype = 'PKBEXTRACT'::bpchar))))));


ALTER TABLE "extract".vwe_extract_pkb_updates OWNER TO ukrdc;

--
-- TOC entry 237 (class 1259 OID 4939662)
-- Name: vwe_extract_pv_pvxml; Type: VIEW; Schema: extract; Owner: ukrdc
--

CREATE VIEW "extract".vwe_extract_pv_pvxml AS
 SELECT pr.pid
   FROM ("extract".patientrecord pr
     JOIN "extract".vwe_pv_members ON (((pr.ukrdcid)::text = (vwe_pv_members.ukrdcid)::text)))
  WHERE (((pr.sendingextract)::text = ANY ((ARRAY['PV'::character varying, 'UKRDC'::character varying])::text[])) AND ((pr.sendingfacility)::text <> ALL ((ARRAY['PV'::character varying, 'PKB'::character varying, 'NHSBT'::character varying, 'TRACING'::character varying])::text[])) AND (pr.repositoryupdatedate > ( SELECT eventcontrol.eventdate
           FROM "extract".eventcontrol
          WHERE (eventcontrol.eventtype = 'PVEXTRACT'::bpchar))));


ALTER TABLE "extract".vwe_extract_pv_pvxml OWNER TO ukrdc;

--
-- TOC entry 234 (class 1259 OID 4792202)
-- Name: vwe_extract_pv_pvxml_eligable; Type: VIEW; Schema: extract; Owner: postgres
--

CREATE VIEW "extract".vwe_extract_pv_pvxml_eligable AS
 SELECT pr.pid
   FROM "extract".patientrecord pr
  WHERE (((pr.sendingextract)::text = ANY (ARRAY[('PV'::character varying)::text, ('UKRDC'::character varying)::text])) AND ((pr.sendingfacility)::text <> 'PV'::text) AND ((pr.ukrdcid)::text IN ( SELECT pr2.ukrdcid
           FROM ("extract".programmembership pm
             JOIN "extract".patientrecord pr2 ON (((pm.pid)::text = (pr2.pid)::text)))
          WHERE (((pm.programname)::text ~~ 'PV.%'::text) AND (pm.totime IS NULL)))));


ALTER TABLE "extract".vwe_extract_pv_pvxml_eligable OWNER TO postgres;

--
-- TOC entry 236 (class 1259 OID 4939657)
-- Name: vwe_extract_pv_rda; Type: VIEW; Schema: extract; Owner: ukrdc
--

CREATE VIEW "extract".vwe_extract_pv_rda AS
 SELECT pr.pid
   FROM "extract".patientrecord pr
  WHERE (((pr.sendingextract)::text = 'SURVEY'::text) AND (pr.repositoryupdatedate > ( SELECT eventcontrol.eventdate
           FROM "extract".eventcontrol
          WHERE (eventcontrol.eventtype = 'PVSURVEYEXTRACT'::bpchar))) AND ((pr.ukrdcid)::text IN ( SELECT pr2.ukrdcid
           FROM ("extract".programmembership pm
             JOIN "extract".patientrecord pr2 ON (((pm.pid)::text = (pr2.pid)::text)))
          WHERE (((pm.programname)::text ~~ 'PV.%'::text) AND (pm.totime IS NULL)))));


ALTER TABLE "extract".vwe_extract_pv_rda OWNER TO ukrdc;

--
-- TOC entry 235 (class 1259 OID 4792211)
-- Name: vwe_extract_radar; Type: VIEW; Schema: extract; Owner: ukrdc
--

CREATE VIEW "extract".vwe_extract_radar AS
 SELECT pr.pid,
    pr.sendingfacility
   FROM "extract".patientrecord pr
  WHERE (((pr.sendingextract)::text = ANY ((ARRAY['PV'::character varying, 'UKRDC'::character varying])::text[])) AND (pr.repositoryupdatedate > ( SELECT eventcontrol.eventdate
           FROM "extract".eventcontrol
          WHERE (eventcontrol.eventtype = 'RADAREXTRACT'::bpchar))) AND ((pr.ukrdcid)::text IN ( SELECT pr2.ukrdcid
           FROM ("extract".programmembership pm
             JOIN "extract".patientrecord pr2 ON (((pm.pid)::text = (pr2.pid)::text)))
          WHERE (((pm.programname)::text = ANY ((ARRAY['RADAR'::character varying, 'NURTURE'::character varying])::text[])) AND (pm.totime IS NULL)))));


ALTER TABLE "extract".vwe_extract_radar OWNER TO ukrdc;

--
-- TOC entry 238 (class 1259 OID 5273415)
-- Name: vwe_survey_data; Type: VIEW; Schema: extract; Owner: ukrdc
--

CREATE VIEW "extract".vwe_survey_data AS
SELECT
    NULL::character varying(30) AS pid,
    NULL::character varying(7) AS sendingfacility,
    NULL::character varying(256) AS sendingfacility_desc,
    NULL::character varying(10) AS main_unit_code,
    NULL::character varying(256) AS main_unit_desc,
    NULL::timestamp without time zone AS repositorycreationdate,
    NULL::character varying(50) AS "NHS Number",
    NULL::character varying(60) AS forename,
    NULL::character varying(60) AS surname,
    NULL::timestamp without time zone AS dob,
    NULL::character varying(100) AS ethnicity,
    NULL::character varying(2) AS gender,
    NULL::character varying(10) AS "Post Code",
    NULL::timestamp without time zone AS "Date Completed",
    NULL::character varying(100) AS enteredatcode,
    NULL::text AS ysq1,
    NULL::text AS ysq2,
    NULL::text AS ysq3,
    NULL::text AS ysq4,
    NULL::text AS ysq5,
    NULL::text AS ysq6,
    NULL::text AS ysq7,
    NULL::text AS ysq8,
    NULL::text AS ysq9,
    NULL::text AS ysq10,
    NULL::text AS ysq11,
    NULL::text AS ysq12,
    NULL::text AS ysq13,
    NULL::text AS ysq14,
    NULL::text AS ysq15,
    NULL::text AS ysq16,
    NULL::text AS ysq17,
    NULL::text AS yohq1,
    NULL::text AS yohq2,
    NULL::text AS yohq3,
    NULL::text AS yohq4,
    NULL::text AS yohq5,
    NULL::text AS myhq1,
    NULL::text AS myhq2,
    NULL::text AS myhq3,
    NULL::text AS myhq4,
    NULL::text AS myhq5,
    NULL::text AS myhq6,
    NULL::text AS myhq7,
    NULL::text AS myhq8,
    NULL::text AS myhq9,
    NULL::text AS myhq10,
    NULL::text AS myhq11,
    NULL::text AS myhq12,
    NULL::text AS myhq13,
    NULL::text AS pam_13_score,
    NULL::text AS pam_13_level,
    NULL::text AS shq1,
    NULL::text AS shq2,
    NULL::text AS shq3,
    NULL::text AS shq4,
    NULL::text AS shq5,
    NULL::text AS shq6,
    NULL::text AS shq7,
    NULL::text AS shq8,
    NULL::text AS shq9,
    NULL::text AS shq10,
    NULL::text AS shq11,
    NULL::text AS shq12,
    NULL::text AS shq13,
    NULL::text AS shq14,
    NULL::text AS shq15,
    NULL::text AS shq16,
    NULL::text AS shq17,
    NULL::text AS yhs1,
    NULL::text AS yhs2,
    NULL::text AS yhs3,
    NULL::text AS yhs4,
    NULL::text AS yhs5,
    NULL::text AS yhs6,
    NULL::text AS yhs,
    NULL::text AS shd,
    NULL::text AS lcc;


ALTER TABLE "extract".vwe_survey_data OWNER TO ukrdc;

--
-- TOC entry 3228 (class 2604 OID 16081065)
-- Name: pkb_links id; Type: DEFAULT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".pkb_links ALTER COLUMN id SET DEFAULT nextval('"extract".pkb_links_id_seq'::regclass);


--
-- TOC entry 3209 (class 2604 OID 4792222)
-- Name: pvdelete did; Type: DEFAULT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".pvdelete ALTER COLUMN did SET DEFAULT nextval('"extract".pvdelete_did_seq'::regclass);


--
-- TOC entry 3222 (class 2604 OID 4792223)
-- Name: validationerror vid; Type: DEFAULT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".validationerror ALTER COLUMN vid SET DEFAULT nextval('"extract".validationerror_vid_seq'::regclass);


--
-- TOC entry 3230 (class 2606 OID 4853250)
-- Name: address address_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".address
    ADD CONSTRAINT address_pkey PRIMARY KEY (id);


--
-- TOC entry 3233 (class 2606 OID 4853252)
-- Name: allergy allergy_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".allergy
    ADD CONSTRAINT allergy_pkey PRIMARY KEY (id);


--
-- TOC entry 3235 (class 2606 OID 4853254)
-- Name: causeofdeath causeofdeath_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".causeofdeath
    ADD CONSTRAINT causeofdeath_pkey PRIMARY KEY (pid);


--
-- TOC entry 3237 (class 2606 OID 4853256)
-- Name: clinicalrelationship clinicalrelationship_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".clinicalrelationship
    ADD CONSTRAINT clinicalrelationship_pkey PRIMARY KEY (id);


--
-- TOC entry 3338 (class 2606 OID 16525248)
-- Name: code_exclusion code_exclusion_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".code_exclusion
    ADD CONSTRAINT code_exclusion_pkey PRIMARY KEY (coding_standard, code, system);


--
-- TOC entry 3239 (class 2606 OID 4853258)
-- Name: code_list code_list_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".code_list
    ADD CONSTRAINT code_list_pkey PRIMARY KEY (coding_standard, code);


--
-- TOC entry 3241 (class 2606 OID 4853260)
-- Name: code_map code_map_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".code_map
    ADD CONSTRAINT code_map_pkey PRIMARY KEY (source_coding_standard, source_code, destination_coding_standard, destination_code);


--
-- TOC entry 3243 (class 2606 OID 4853262)
-- Name: contactdetail contactdetail_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".contactdetail
    ADD CONSTRAINT contactdetail_pkey PRIMARY KEY (id);


--
-- TOC entry 3246 (class 2606 OID 4853264)
-- Name: diagnosis diagnosis_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".diagnosis
    ADD CONSTRAINT diagnosis_pkey PRIMARY KEY (id);


--
-- TOC entry 3249 (class 2606 OID 4853266)
-- Name: dialysissession dialysissession_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".dialysissession
    ADD CONSTRAINT dialysissession_pkey PRIMARY KEY (id);


--
-- TOC entry 3252 (class 2606 OID 4853268)
-- Name: document document_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".document
    ADD CONSTRAINT document_pkey PRIMARY KEY (id);


--
-- TOC entry 3255 (class 2606 OID 4853270)
-- Name: encounter encounter_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".encounter
    ADD CONSTRAINT encounter_pkey PRIMARY KEY (id);


--
-- TOC entry 3257 (class 2606 OID 4853272)
-- Name: eventcontrol eventcontrol_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".eventcontrol
    ADD CONSTRAINT eventcontrol_pkey PRIMARY KEY (eventtype);


--
-- TOC entry 3259 (class 2606 OID 4853274)
-- Name: familydoctor familydoctor_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".familydoctor
    ADD CONSTRAINT familydoctor_pkey PRIMARY KEY (id);


--
-- TOC entry 3261 (class 2606 OID 4853276)
-- Name: familyhistory familyhistory_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".familyhistory
    ADD CONSTRAINT familyhistory_pkey PRIMARY KEY (id);


--
-- TOC entry 3334 (class 2606 OID 14070606)
-- Name: facility firstkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".facility
    ADD CONSTRAINT firstkey PRIMARY KEY (code);


--
-- TOC entry 3265 (class 2606 OID 4853296)
-- Name: laborder laborder_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".laborder
    ADD CONSTRAINT laborder_pkey PRIMARY KEY (id);


--
-- TOC entry 3269 (class 2606 OID 4853278)
-- Name: level level_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".level
    ADD CONSTRAINT level_pkey PRIMARY KEY (id);


--
-- TOC entry 3272 (class 2606 OID 4853280)
-- Name: medication medication_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".medication
    ADD CONSTRAINT medication_pkey PRIMARY KEY (id);


--
-- TOC entry 3275 (class 2606 OID 4853282)
-- Name: name name_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".name
    ADD CONSTRAINT name_pkey PRIMARY KEY (id);


--
-- TOC entry 3279 (class 2606 OID 4853284)
-- Name: observation observation_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".observation
    ADD CONSTRAINT observation_pkey PRIMARY KEY (id);


--
-- TOC entry 3281 (class 2606 OID 4853294)
-- Name: optout optout_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".optout
    ADD CONSTRAINT optout_pkey PRIMARY KEY (id);


--
-- TOC entry 3283 (class 2606 OID 4853298)
-- Name: patient patient_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".patient
    ADD CONSTRAINT patient_pkey PRIMARY KEY (pid);


--
-- TOC entry 3287 (class 2606 OID 4853300)
-- Name: patientnumber patientnumber_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".patientnumber
    ADD CONSTRAINT patientnumber_pkey PRIMARY KEY (id);


--
-- TOC entry 3290 (class 2606 OID 4853302)
-- Name: patientrecord patientrecord_key2; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".patientrecord
    ADD CONSTRAINT patientrecord_key2 UNIQUE (sendingfacility, sendingextract, localpatientid);


--
-- TOC entry 3292 (class 2606 OID 4853304)
-- Name: patientrecord patientrecord_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".patientrecord
    ADD CONSTRAINT patientrecord_pkey PRIMARY KEY (pid);


--
-- TOC entry 3328 (class 2606 OID 15156456)
-- Name: ukrdc_ods_gp_codes pk_ukrdc_ods_gp_codes; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".ukrdc_ods_gp_codes
    ADD CONSTRAINT pk_ukrdc_ods_gp_codes PRIMARY KEY (code);


--
-- TOC entry 3336 (class 2606 OID 16081070)
-- Name: pkb_links pkb_links_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".pkb_links
    ADD CONSTRAINT pkb_links_pkey PRIMARY KEY (id);


--
-- TOC entry 3294 (class 2606 OID 4853306)
-- Name: procedure procedure_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".procedure
    ADD CONSTRAINT procedure_pkey PRIMARY KEY (id);


--
-- TOC entry 3297 (class 2606 OID 4853308)
-- Name: programmembership programmembership_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".programmembership
    ADD CONSTRAINT programmembership_pkey PRIMARY KEY (id);


--
-- TOC entry 3299 (class 2606 OID 4853310)
-- Name: pvdata pvdata_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".pvdata
    ADD CONSTRAINT pvdata_pkey PRIMARY KEY (id);


--
-- TOC entry 3302 (class 2606 OID 4853312)
-- Name: pvdelete pvdelete_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".pvdelete
    ADD CONSTRAINT pvdelete_pkey PRIMARY KEY (did);


--
-- TOC entry 3304 (class 2606 OID 4853314)
-- Name: question question_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".question
    ADD CONSTRAINT question_pkey PRIMARY KEY (id);


--
-- TOC entry 3306 (class 2606 OID 4853316)
-- Name: renaldiagnosis renaldiagnosis_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".renaldiagnosis
    ADD CONSTRAINT renaldiagnosis_pkey PRIMARY KEY (pid);


--
-- TOC entry 3310 (class 2606 OID 4853318)
-- Name: resultitem resultitem_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".resultitem
    ADD CONSTRAINT resultitem_pkey PRIMARY KEY (id);


--
-- TOC entry 3312 (class 2606 OID 4853320)
-- Name: satellite_map satellite_map_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".satellite_map
    ADD CONSTRAINT satellite_map_pkey PRIMARY KEY (satellite_code, main_unit_code);


--
-- TOC entry 3314 (class 2606 OID 4853322)
-- Name: score score_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".score
    ADD CONSTRAINT score_pkey PRIMARY KEY (id);


--
-- TOC entry 3316 (class 2606 OID 4853324)
-- Name: socialhistory socialhistory_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".socialhistory
    ADD CONSTRAINT socialhistory_pkey PRIMARY KEY (id);


--
-- TOC entry 3318 (class 2606 OID 4853326)
-- Name: survey survey_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".survey
    ADD CONSTRAINT survey_pkey PRIMARY KEY (id);


--
-- TOC entry 3320 (class 2606 OID 4853328)
-- Name: transplant transplant_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".transplant
    ADD CONSTRAINT transplant_pkey PRIMARY KEY (id);


--
-- TOC entry 3322 (class 2606 OID 4853330)
-- Name: transplantlist transplantlist_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".transplantlist
    ADD CONSTRAINT transplantlist_pkey PRIMARY KEY (id);


--
-- TOC entry 3326 (class 2606 OID 4853332)
-- Name: treatment treatment_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".treatment
    ADD CONSTRAINT treatment_pkey PRIMARY KEY (id);


--
-- TOC entry 3330 (class 2606 OID 4853334)
-- Name: validationerror validationerror_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".validationerror
    ADD CONSTRAINT validationerror_pkey PRIMARY KEY (vid);


--
-- TOC entry 3332 (class 2606 OID 4853336)
-- Name: vascularaccess vascularaccess_pkey; Type: CONSTRAINT; Schema: extract; Owner: ukrdc
--

ALTER TABLE ONLY "extract".vascularaccess
    ADD CONSTRAINT vascularaccess_pkey PRIMARY KEY (id);


--
-- TOC entry 3231 (class 1259 OID 15156461)
-- Name: ix_address_pid; Type: INDEX; Schema: extract; Owner: ukrdc
--

CREATE INDEX ix_address_pid ON "extract".address USING btree (pid);


--
-- TOC entry 3244 (class 1259 OID 15156459)
-- Name: ix_contactdetail_pid; Type: INDEX; Schema: extract; Owner: ukrdc
--

CREATE INDEX ix_contactdetail_pid ON "extract".contactdetail USING btree (pid);


--
-- TOC entry 3247 (class 1259 OID 15156463)
-- Name: ix_diagnosis_pid; Type: INDEX; Schema: extract; Owner: ukrdc
--

CREATE INDEX ix_diagnosis_pid ON "extract".diagnosis USING btree (pid);


--
-- TOC entry 3250 (class 1259 OID 15156457)
-- Name: ix_dialysissession_pid; Type: INDEX; Schema: extract; Owner: ukrdc
--

CREATE INDEX ix_dialysissession_pid ON "extract".dialysissession USING btree (pid);


--
-- TOC entry 3253 (class 1259 OID 15156458)
-- Name: ix_document_pid; Type: INDEX; Schema: extract; Owner: ukrdc
--

CREATE INDEX ix_document_pid ON "extract".document USING btree (pid);


--
-- TOC entry 3276 (class 1259 OID 15156464)
-- Name: ix_observation_pid_obstime; Type: INDEX; Schema: extract; Owner: ukrdc
--

CREATE INDEX ix_observation_pid_obstime ON "extract".observation USING btree (pid, observationtime);


--
-- TOC entry 3288 (class 1259 OID 15156454)
-- Name: ix_patientrecord_ukrdcid; Type: INDEX; Schema: extract; Owner: ukrdc
--

CREATE INDEX ix_patientrecord_ukrdcid ON "extract".patientrecord USING btree (ukrdcid);


--
-- TOC entry 3295 (class 1259 OID 15156460)
-- Name: ix_programmembership_pid; Type: INDEX; Schema: extract; Owner: ukrdc
--

CREATE INDEX ix_programmembership_pid ON "extract".programmembership USING btree (pid);


--
-- TOC entry 3300 (class 1259 OID 15156462)
-- Name: ix_pvdelete_pid; Type: INDEX; Schema: extract; Owner: ukrdc
--

CREATE INDEX ix_pvdelete_pid ON "extract".pvdelete USING btree (pid);


--
-- TOC entry 3323 (class 1259 OID 15156452)
-- Name: ix_treatment_pid; Type: INDEX; Schema: extract; Owner: ukrdc
--

CREATE INDEX ix_treatment_pid ON "extract".treatment USING btree (pid);


--
-- TOC entry 3324 (class 1259 OID 15156453)
-- Name: ix_treatment_pid_fromtime; Type: INDEX; Schema: extract; Owner: ukrdc
--

CREATE INDEX ix_treatment_pid_fromtime ON "extract".treatment USING btree (pid, fromtime);


--
-- TOC entry 3262 (class 1259 OID 18638657)
-- Name: laborder_creation_date_idx; Type: INDEX; Schema: extract; Owner: ukrdc
--

CREATE INDEX laborder_creation_date_idx ON "extract".laborder USING btree (creation_date);


--
-- TOC entry 3263 (class 1259 OID 4853337)
-- Name: laborder_pid_idx; Type: INDEX; Schema: extract; Owner: ukrdc
--

CREATE INDEX laborder_pid_idx ON "extract".laborder USING btree (pid);


--
-- TOC entry 3266 (class 1259 OID 18638659)
-- Name: laborder_repository_update_date_idx; Type: INDEX; Schema: extract; Owner: ukrdc
--

CREATE INDEX laborder_repository_update_date_idx ON "extract".laborder USING btree (repository_update_date);


--
-- TOC entry 3267 (class 1259 OID 18638658)
-- Name: laborder_update_date_idx; Type: INDEX; Schema: extract; Owner: ukrdc
--

CREATE INDEX laborder_update_date_idx ON "extract".laborder USING btree (update_date);


--
-- TOC entry 3270 (class 1259 OID 4853338)
-- Name: medication_pid_idx; Type: INDEX; Schema: extract; Owner: ukrdc
--

CREATE INDEX medication_pid_idx ON "extract".medication USING btree (pid);


--
-- TOC entry 3273 (class 1259 OID 4853339)
-- Name: name_pid_idx; Type: INDEX; Schema: extract; Owner: ukrdc
--

CREATE INDEX name_pid_idx ON "extract".name USING btree (pid);


--
-- TOC entry 3277 (class 1259 OID 4853340)
-- Name: observation_pid_idx; Type: INDEX; Schema: extract; Owner: ukrdc
--

CREATE INDEX observation_pid_idx ON "extract".observation USING btree (pid);


--
-- TOC entry 3284 (class 1259 OID 5136251)
-- Name: patientnumber_patientid; Type: INDEX; Schema: extract; Owner: ukrdc
--

CREATE INDEX patientnumber_patientid ON "extract".patientnumber USING btree (patientid);


--
-- TOC entry 3285 (class 1259 OID 4853341)
-- Name: patientnumber_pid_idx; Type: INDEX; Schema: extract; Owner: ukrdc
--

CREATE INDEX patientnumber_pid_idx ON "extract".patientnumber USING btree (pid);


--
-- TOC entry 3307 (class 1259 OID 4853342)
-- Name: resultitem_orderid_firstpart; Type: INDEX; Schema: extract; Owner: ukrdc
--

CREATE INDEX resultitem_orderid_firstpart ON "extract".resultitem USING btree ("left"((orderid)::text, '-32'::integer));


--
-- TOC entry 3308 (class 1259 OID 4853343)
-- Name: resultitem_orderid_idx; Type: INDEX; Schema: extract; Owner: ukrdc
--

CREATE INDEX resultitem_orderid_idx ON "extract".resultitem USING btree (orderid);


--
-- TOC entry 3502 (class 2618 OID 5273418)
-- Name: vwe_survey_data _RETURN; Type: RULE; Schema: extract; Owner: ukrdc
--

CREATE OR REPLACE VIEW "extract".vwe_survey_data AS
 SELECT a.pid,
    a.sendingfacility,
    i.description AS sendingfacility_desc,
        CASE
            WHEN (k.main_unit_code IS NOT NULL) THEN k.main_unit_code
            ELSE l.main_unit_code
        END AS main_unit_code,
        CASE
            WHEN (k.main_unit_code IS NOT NULL) THEN m.description
            ELSE n.description
        END AS main_unit_desc,
    a.repositorycreationdate,
    h.patientid AS "NHS Number",
    g.given AS forename,
    g.family AS surname,
    f.birthtime AS dob,
    f.ethnicgroupdesc AS ethnicity,
    f.gender,
    j.postcode AS "Post Code",
    b.surveytime AS "Date Completed",
    b.enteredatcode,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'YSQ1'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS ysq1,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'YSQ2'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS ysq2,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'YSQ3'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS ysq3,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'YSQ4'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS ysq4,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'YSQ5'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS ysq5,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'YSQ6'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS ysq6,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'YSQ7'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS ysq7,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'YSQ8'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS ysq8,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'YSQ9'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS ysq9,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'YSQ10'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS ysq10,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'YSQ11'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS ysq11,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'YSQ12'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS ysq12,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'YSQ13'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS ysq13,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'YSQ14'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS ysq14,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'YSQ15'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS ysq15,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'YSQ16'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS ysq16,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'YSQ17'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS ysq17,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'YOHQ1'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS yohq1,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'YOHQ2'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS yohq2,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'YOHQ3'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS yohq3,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'YOHQ4'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS yohq4,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'YOHQ5'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS yohq5,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'MYHQ1'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS myhq1,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'MYHQ2'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS myhq2,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'MYHQ3'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS myhq3,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'MYHQ4'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS myhq4,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'MYHQ5'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS myhq5,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'MYHQ6'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS myhq6,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'MYHQ7'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS myhq7,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'MYHQ8'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS myhq8,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'MYHQ9'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS myhq9,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'MYHQ10'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS myhq10,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'MYHQ11'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS myhq11,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'MYHQ12'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS myhq12,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'MYHQ13'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS myhq13,
    max((
        CASE
            WHEN ((d.scoretypecode)::text = '925431000000109'::text) THEN d.scorevalue
            ELSE NULL::character varying
        END)::text) AS pam_13_score,
    max((
        CASE
            WHEN ((e.leveltypecode)::text = '962851000000103'::text) THEN e.levelvalue
            ELSE NULL::character varying
        END)::text) AS pam_13_level,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'SHQ1'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS shq1,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'SHQ2'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS shq2,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'SHQ3'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS shq3,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'SHQ4'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS shq4,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'SHQ5'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS shq5,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'SHQ6'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS shq6,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'SHQ7'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS shq7,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'SHQ8'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS shq8,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'SHQ9'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS shq9,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'SHQ10'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS shq10,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'SHQ11'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS shq11,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'SHQ12'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS shq12,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'SHQ13'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS shq13,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'SHQ14'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS shq14,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'SHQ15'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS shq15,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'SHQ16'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS shq16,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'SHQ17'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS shq17,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'YHS1'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS yhs1,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'YHS2'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS yhs2,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'YHS3'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS yhs3,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'YHS4'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS yhs4,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'YHS5'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS yhs5,
    max((
        CASE
            WHEN ((c.questiontypecode)::text = 'YHS6'::text) THEN c.response
            ELSE NULL::character varying
        END)::text) AS yhs6,
        CASE
            WHEN (pm_yhs.pid IS NOT NULL) THEN 'YES'::text
            ELSE NULL::text
        END AS yhs,
        CASE
            WHEN (pm_shd.pid IS NOT NULL) THEN 'YES'::text
            ELSE NULL::text
        END AS shd,
        CASE
            WHEN (pm_lcc.pid IS NOT NULL) THEN 'YES'::text
            ELSE NULL::text
        END AS lcc
   FROM (((((((((((((((("extract".patientrecord a
     LEFT JOIN "extract".survey b ON (((a.pid)::text = (b.pid)::text)))
     LEFT JOIN "extract".question c ON (((b.id)::text = (c.surveyid)::text)))
     LEFT JOIN "extract".score d ON (((b.id)::text = (d.surveyid)::text)))
     LEFT JOIN "extract".level e ON (((b.id)::text = (e.surveyid)::text)))
     LEFT JOIN "extract".patient f ON (((a.pid)::text = (f.pid)::text)))
     LEFT JOIN "extract".name g ON ((((a.pid)::text = (g.pid)::text) AND ((g.nameuse)::text = 'L'::text))))
     LEFT JOIN "extract".patientnumber h ON (((a.pid)::text = (h.pid)::text)))
     LEFT JOIN "extract".code_list i ON ((((a.sendingfacility)::text = (i.code)::text) AND ((i.coding_standard)::text = 'RR1+'::text))))
     LEFT JOIN "extract".address j ON (((a.pid)::text = (j.pid)::text)))
     LEFT JOIN "extract".satellite_map k ON (((a.sendingfacility)::text = (k.satellite_code)::text)))
     LEFT JOIN "extract".satellite_map l ON (((a.sendingfacility)::text = (l.main_unit_code)::text)))
     LEFT JOIN "extract".code_list m ON ((((k.main_unit_code)::text = (m.code)::text) AND ((m.coding_standard)::text = 'RR1+'::text))))
     LEFT JOIN "extract".code_list n ON ((((l.main_unit_code)::text = (n.code)::text) AND ((n.coding_standard)::text = 'RR1+'::text))))
     LEFT JOIN "extract".programmembership pm_yhs ON ((((a.pid)::text = (pm_yhs.pid)::text) AND ((pm_yhs.programname)::text = 'YHS'::text))))
     LEFT JOIN "extract".programmembership pm_shd ON ((((a.pid)::text = (pm_shd.pid)::text) AND ((pm_shd.programname)::text = 'SHD'::text))))
     LEFT JOIN "extract".programmembership pm_lcc ON ((((a.pid)::text = (pm_lcc.pid)::text) AND ((pm_lcc.programname)::text = 'LCC'::text))))
  WHERE ((a.sendingextract)::text = 'SURVEY'::text)
  GROUP BY a.pid, a.sendingfacility, i.description, k.main_unit_code, l.main_unit_code, m.description, n.description, a.repositorycreationdate, g.given, g.family, h.patientid, f.birthtime, f.gender, f.ethnicgroupdesc, j.postcode, b.surveytime, b.enteredatcode, pm_yhs.pid, pm_shd.pid, pm_lcc.pid
  ORDER BY a.repositoryupdatedate, a.pid;


--
-- TOC entry 3369 (class 2620 OID 15156575)
-- Name: resultitem trg_set_laborder_repository_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_laborder_repository_update_date AFTER INSERT OR DELETE OR UPDATE ON "extract".resultitem FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_laborder_repository_update_date();


--
-- TOC entry 3339 (class 2620 OID 15156545)
-- Name: address trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".address FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3340 (class 2620 OID 15156541)
-- Name: allergy trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".allergy FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3341 (class 2620 OID 15156547)
-- Name: causeofdeath trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".causeofdeath FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3342 (class 2620 OID 15156538)
-- Name: clinicalrelationship trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".clinicalrelationship FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3343 (class 2620 OID 15156567)
-- Name: code_list trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".code_list FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3344 (class 2620 OID 15156534)
-- Name: code_map trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".code_map FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3345 (class 2620 OID 15156542)
-- Name: contactdetail trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".contactdetail FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3346 (class 2620 OID 15156536)
-- Name: diagnosis trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".diagnosis FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3347 (class 2620 OID 15156548)
-- Name: dialysissession trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".dialysissession FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3348 (class 2620 OID 15156549)
-- Name: document trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".document FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3349 (class 2620 OID 15156546)
-- Name: encounter trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".encounter FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3350 (class 2620 OID 15156539)
-- Name: eventcontrol trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".eventcontrol FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3380 (class 2620 OID 15156533)
-- Name: facility trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".facility FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3351 (class 2620 OID 15156543)
-- Name: familydoctor trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".familydoctor FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3352 (class 2620 OID 15156544)
-- Name: familyhistory trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".familyhistory FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3353 (class 2620 OID 15156540)
-- Name: laborder trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".laborder FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3354 (class 2620 OID 15156550)
-- Name: level trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".level FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3355 (class 2620 OID 15156537)
-- Name: medication trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".medication FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3356 (class 2620 OID 15156551)
-- Name: name trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".name FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3357 (class 2620 OID 15156552)
-- Name: observation trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".observation FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3358 (class 2620 OID 15156554)
-- Name: optout trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".optout FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3359 (class 2620 OID 15156553)
-- Name: patient trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".patient FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3360 (class 2620 OID 15156555)
-- Name: patientnumber trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".patientnumber FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3361 (class 2620 OID 15156556)
-- Name: patientrecord trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".patientrecord FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3362 (class 2620 OID 15156557)
-- Name: procedure trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".procedure FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3363 (class 2620 OID 15156558)
-- Name: programmembership trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".programmembership FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3364 (class 2620 OID 15156559)
-- Name: pvdata trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".pvdata FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3365 (class 2620 OID 15156560)
-- Name: pvdelete trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".pvdelete FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3366 (class 2620 OID 15156562)
-- Name: question trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".question FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3367 (class 2620 OID 15156565)
-- Name: renaldiagnosis trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".renaldiagnosis FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3368 (class 2620 OID 15156566)
-- Name: resultitem trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".resultitem FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3370 (class 2620 OID 15156535)
-- Name: satellite_map trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".satellite_map FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3371 (class 2620 OID 15156561)
-- Name: score trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".score FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3372 (class 2620 OID 15156563)
-- Name: socialhistory trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".socialhistory FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3373 (class 2620 OID 15156564)
-- Name: survey trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".survey FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3374 (class 2620 OID 15156571)
-- Name: transplant trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".transplant FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3375 (class 2620 OID 15156572)
-- Name: transplantlist trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".transplantlist FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3376 (class 2620 OID 15156573)
-- Name: treatment trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".treatment FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3377 (class 2620 OID 15156570)
-- Name: ukrdc_ods_gp_codes trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".ukrdc_ods_gp_codes FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3378 (class 2620 OID 15156568)
-- Name: validationerror trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".validationerror FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3379 (class 2620 OID 15156569)
-- Name: vascularaccess trg_set_update_date; Type: TRIGGER; Schema: extract; Owner: ukrdc
--

CREATE TRIGGER trg_set_update_date BEFORE UPDATE ON "extract".vascularaccess FOR EACH ROW EXECUTE PROCEDURE "extract".trigger_fnc_set_update_date();


--
-- TOC entry 3516 (class 0 OID 0)
-- Dependencies: 9
-- Name: SCHEMA "extract"; Type: ACL; Schema: -; Owner: postgres
--

GRANT ALL ON SCHEMA "extract" TO ukrdc;


--
-- TOC entry 3518 (class 0 OID 0)
-- Dependencies: 192
-- Name: TABLE address; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".address TO identifychanges;


--
-- TOC entry 3519 (class 0 OID 0)
-- Dependencies: 193
-- Name: TABLE allergy; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".allergy TO identifychanges;


--
-- TOC entry 3520 (class 0 OID 0)
-- Dependencies: 194
-- Name: TABLE causeofdeath; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".causeofdeath TO identifychanges;


--
-- TOC entry 3521 (class 0 OID 0)
-- Dependencies: 195
-- Name: TABLE clinicalrelationship; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".clinicalrelationship TO identifychanges;


--
-- TOC entry 3522 (class 0 OID 0)
-- Dependencies: 250
-- Name: TABLE code_exclusion; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".code_exclusion TO identifychanges;


--
-- TOC entry 3523 (class 0 OID 0)
-- Dependencies: 196
-- Name: TABLE code_list; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".code_list TO identifychanges;


--
-- TOC entry 3524 (class 0 OID 0)
-- Dependencies: 197
-- Name: TABLE code_map; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".code_map TO identifychanges;


--
-- TOC entry 3525 (class 0 OID 0)
-- Dependencies: 198
-- Name: TABLE contactdetail; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".contactdetail TO identifychanges;


--
-- TOC entry 3526 (class 0 OID 0)
-- Dependencies: 199
-- Name: TABLE diagnosis; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".diagnosis TO identifychanges;


--
-- TOC entry 3527 (class 0 OID 0)
-- Dependencies: 200
-- Name: TABLE dialysissession; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".dialysissession TO identifychanges;


--
-- TOC entry 3528 (class 0 OID 0)
-- Dependencies: 201
-- Name: TABLE document; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".document TO identifychanges;


--
-- TOC entry 3529 (class 0 OID 0)
-- Dependencies: 202
-- Name: TABLE encounter; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".encounter TO identifychanges;


--
-- TOC entry 3530 (class 0 OID 0)
-- Dependencies: 203
-- Name: TABLE eventcontrol; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT ALL ON TABLE "extract".eventcontrol TO identifychanges;


--
-- TOC entry 3531 (class 0 OID 0)
-- Dependencies: 239
-- Name: TABLE facility; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".facility TO identifychanges;


--
-- TOC entry 3532 (class 0 OID 0)
-- Dependencies: 204
-- Name: TABLE familydoctor; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".familydoctor TO identifychanges;


--
-- TOC entry 3533 (class 0 OID 0)
-- Dependencies: 205
-- Name: TABLE familyhistory; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".familyhistory TO identifychanges;


--
-- TOC entry 3534 (class 0 OID 0)
-- Dependencies: 206
-- Name: TABLE laborder; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".laborder TO identifychanges;


--
-- TOC entry 3535 (class 0 OID 0)
-- Dependencies: 207
-- Name: TABLE level; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".level TO identifychanges;


--
-- TOC entry 3536 (class 0 OID 0)
-- Dependencies: 208
-- Name: TABLE medication; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".medication TO identifychanges;


--
-- TOC entry 3537 (class 0 OID 0)
-- Dependencies: 209
-- Name: TABLE name; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".name TO identifychanges;


--
-- TOC entry 3538 (class 0 OID 0)
-- Dependencies: 210
-- Name: TABLE observation; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".observation TO identifychanges;


--
-- TOC entry 3539 (class 0 OID 0)
-- Dependencies: 211
-- Name: TABLE optout; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".optout TO identifychanges;


--
-- TOC entry 3540 (class 0 OID 0)
-- Dependencies: 212
-- Name: TABLE patient; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".patient TO identifychanges;


--
-- TOC entry 3541 (class 0 OID 0)
-- Dependencies: 213
-- Name: TABLE patientnumber; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".patientnumber TO identifychanges;


--
-- TOC entry 3542 (class 0 OID 0)
-- Dependencies: 214
-- Name: TABLE patientrecord; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".patientrecord TO identifychanges;


--
-- TOC entry 3543 (class 0 OID 0)
-- Dependencies: 249
-- Name: TABLE pkb_links; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".pkb_links TO identifychanges;


--
-- TOC entry 3545 (class 0 OID 0)
-- Dependencies: 248
-- Name: SEQUENCE pkb_links_id_seq; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON SEQUENCE "extract".pkb_links_id_seq TO identifychanges;


--
-- TOC entry 3546 (class 0 OID 0)
-- Dependencies: 215
-- Name: TABLE procedure; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".procedure TO identifychanges;


--
-- TOC entry 3547 (class 0 OID 0)
-- Dependencies: 216
-- Name: TABLE programmembership; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".programmembership TO identifychanges;


--
-- TOC entry 3548 (class 0 OID 0)
-- Dependencies: 217
-- Name: TABLE pvdata; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".pvdata TO identifychanges;


--
-- TOC entry 3549 (class 0 OID 0)
-- Dependencies: 218
-- Name: TABLE pvdelete; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".pvdelete TO identifychanges;


--
-- TOC entry 3551 (class 0 OID 0)
-- Dependencies: 219
-- Name: SEQUENCE pvdelete_did_seq; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON SEQUENCE "extract".pvdelete_did_seq TO identifychanges;


--
-- TOC entry 3552 (class 0 OID 0)
-- Dependencies: 220
-- Name: TABLE question; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".question TO identifychanges;


--
-- TOC entry 3553 (class 0 OID 0)
-- Dependencies: 221
-- Name: TABLE renaldiagnosis; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".renaldiagnosis TO identifychanges;


--
-- TOC entry 3554 (class 0 OID 0)
-- Dependencies: 222
-- Name: TABLE resultitem; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".resultitem TO identifychanges;


--
-- TOC entry 3555 (class 0 OID 0)
-- Dependencies: 223
-- Name: TABLE satellite_map; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".satellite_map TO identifychanges;


--
-- TOC entry 3556 (class 0 OID 0)
-- Dependencies: 224
-- Name: TABLE score; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".score TO identifychanges;


--
-- TOC entry 3557 (class 0 OID 0)
-- Dependencies: 225
-- Name: TABLE socialhistory; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".socialhistory TO identifychanges;


--
-- TOC entry 3558 (class 0 OID 0)
-- Dependencies: 226
-- Name: TABLE survey; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".survey TO identifychanges;


--
-- TOC entry 3559 (class 0 OID 0)
-- Dependencies: 227
-- Name: TABLE transplant; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".transplant TO identifychanges;


--
-- TOC entry 3560 (class 0 OID 0)
-- Dependencies: 228
-- Name: TABLE transplantlist; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".transplantlist TO identifychanges;


--
-- TOC entry 3561 (class 0 OID 0)
-- Dependencies: 229
-- Name: TABLE treatment; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".treatment TO identifychanges;


--
-- TOC entry 3562 (class 0 OID 0)
-- Dependencies: 230
-- Name: TABLE ukrdc_ods_gp_codes; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".ukrdc_ods_gp_codes TO identifychanges;


--
-- TOC entry 3563 (class 0 OID 0)
-- Dependencies: 231
-- Name: TABLE validationerror; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".validationerror TO identifychanges;


--
-- TOC entry 3565 (class 0 OID 0)
-- Dependencies: 232
-- Name: SEQUENCE validationerror_vid_seq; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON SEQUENCE "extract".validationerror_vid_seq TO identifychanges;


--
-- TOC entry 3566 (class 0 OID 0)
-- Dependencies: 233
-- Name: TABLE vascularaccess; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".vascularaccess TO identifychanges;


--
-- TOC entry 3567 (class 0 OID 0)
-- Dependencies: 242
-- Name: TABLE vwe_pkb_members; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".vwe_pkb_members TO identifychanges;


--
-- TOC entry 3568 (class 0 OID 0)
-- Dependencies: 246
-- Name: TABLE vwe_extract_pkb_deceased; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".vwe_extract_pkb_deceased TO identifychanges;


--
-- TOC entry 3569 (class 0 OID 0)
-- Dependencies: 241
-- Name: TABLE vwe_pkb_test_patients; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".vwe_pkb_test_patients TO identifychanges;


--
-- TOC entry 3570 (class 0 OID 0)
-- Dependencies: 245
-- Name: TABLE vwe_extract_pkb_deceased_test; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".vwe_extract_pkb_deceased_test TO identifychanges;


--
-- TOC entry 3571 (class 0 OID 0)
-- Dependencies: 240
-- Name: TABLE vwe_pv_members; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".vwe_pv_members TO identifychanges;


--
-- TOC entry 3572 (class 0 OID 0)
-- Dependencies: 244
-- Name: TABLE vwe_extract_pkb_new; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".vwe_extract_pkb_new TO identifychanges;


--
-- TOC entry 3573 (class 0 OID 0)
-- Dependencies: 243
-- Name: TABLE vwe_extract_pkb_new_test; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".vwe_extract_pkb_new_test TO identifychanges;


--
-- TOC entry 3574 (class 0 OID 0)
-- Dependencies: 247
-- Name: TABLE vwe_extract_pkb_updates; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".vwe_extract_pkb_updates TO identifychanges;


--
-- TOC entry 3575 (class 0 OID 0)
-- Dependencies: 237
-- Name: TABLE vwe_extract_pv_pvxml; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".vwe_extract_pv_pvxml TO identifychanges;


--
-- TOC entry 3576 (class 0 OID 0)
-- Dependencies: 234
-- Name: TABLE vwe_extract_pv_pvxml_eligable; Type: ACL; Schema: extract; Owner: postgres
--

GRANT ALL ON TABLE "extract".vwe_extract_pv_pvxml_eligable TO ukrdc;
GRANT SELECT ON TABLE "extract".vwe_extract_pv_pvxml_eligable TO identifychanges;


--
-- TOC entry 3577 (class 0 OID 0)
-- Dependencies: 236
-- Name: TABLE vwe_extract_pv_rda; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".vwe_extract_pv_rda TO identifychanges;


--
-- TOC entry 3578 (class 0 OID 0)
-- Dependencies: 235
-- Name: TABLE vwe_extract_radar; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".vwe_extract_radar TO identifychanges;


--
-- TOC entry 3579 (class 0 OID 0)
-- Dependencies: 238
-- Name: TABLE vwe_survey_data; Type: ACL; Schema: extract; Owner: ukrdc
--

GRANT SELECT ON TABLE "extract".vwe_survey_data TO identifychanges;


--
-- TOC entry 1958 (class 826 OID 4853346)
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: extract; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA "extract" GRANT SELECT,USAGE ON SEQUENCES  TO ukrdc;


--
-- TOC entry 1959 (class 826 OID 4853347)
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: extract; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA "extract" GRANT SELECT,INSERT,DELETE,UPDATE ON TABLES  TO ukrdc;


--
-- TOC entry 1960 (class 826 OID 4853348)
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: public; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT SELECT,USAGE ON SEQUENCES  TO ukrdc;


--
-- TOC entry 1961 (class 826 OID 4853349)
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT SELECT,INSERT,DELETE,UPDATE ON TABLES  TO ukrdc;


-- Completed on 2022-08-24 06:28:49

--
-- PostgreSQL database dump complete
--

