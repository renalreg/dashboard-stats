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

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT SELECT,USAGE ON SEQUENCES  TO ukrdc;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT SELECT,INSERT,DELETE,UPDATE ON TABLES  TO ukrdc;




