--
-- PostgreSQL database dump
--

-- Dumped from database version 14.18 (Debian 14.18-1.pgdg120+1)
-- Dumped by pg_dump version 14.18 (Debian 14.18-1.pgdg120+1)

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
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: bronze_stories; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.bronze_stories (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    title character varying(500),
    content text,
    source character varying(100),
    source_url character varying(1000),
    author character varying(100),
    post_date timestamp with time zone,
    scraped_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    raw_metadata jsonb
);


ALTER TABLE public.bronze_stories OWNER TO postgres;

--
-- Name: bronze_story_processing; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.bronze_story_processing (
    story_id uuid NOT NULL,
    processing_status character varying(50) DEFAULT 'pending'::character varying,
    processing_metadata jsonb,
    error_message text,
    retry_count integer DEFAULT 0,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.bronze_story_processing OWNER TO postgres;

--
-- Name: silver_story_chunks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.silver_story_chunks (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    story_id uuid,
    chunk_text text NOT NULL,
    chunk_context text,
    chunk_order integer NOT NULL,
    chunk_type character varying(50),
    overlap_start integer DEFAULT 0,
    overlap_end integer DEFAULT 0,
    content_embedding text,
    search_embedding text,
    chunk_length integer,
    chunk_word_count integer,
    semantic_keywords text[],
    embedding_model character varying(100),
    embedding_version character varying(50),
    embedding_model_version character varying(100),
    processing_language character varying(10),
    chunk_quality_score double precision,
    embedding_cost double precision DEFAULT 0.0,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.silver_story_chunks OWNER TO postgres;

--
-- Data for Name: bronze_stories; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.bronze_stories (id, title, content, source, source_url, author, post_date, scraped_at, raw_metadata) FROM stdin;
173113cd-bebf-4a96-bdb8-b833d7fa14ee	The Haunted House on Elm Street	It was a dark and stormy night when I first encountered the ghostly presence in the old Victorian house. The floorboards creaked ominously as I climbed the stairs, and I could feel unseen eyes watching my every move. The temperature dropped suddenly, and my breath became visible in the frigid air. Then I heard it - a whisper so faint it could have been the wind, but the words were unmistakably clear: "Get out... before it's too late." I should have listened to that warning, but curiosity got the better of me. What I discovered in that attic changed my life forever.	reddit_ghoststories	\N	user123	\N	2025-07-25 15:38:53.034829+00	\N
d938dbbe-5542-4794-8dc6-3b23d6e9a55a	The Midnight Visitor	Every night at exactly 3:33 AM, I would hear footsteps in the hallway outside my bedroom. At first, I thought it was just the house settling, but the pattern was too regular, too deliberate. The footsteps would start at the top of the stairs, slowly make their way down the hall, and stop right outside my door. I could see the shadow of feet blocking the light from under the door. But whenever I gathered the courage to look, there was nothing there. This went on for weeks until one night, I decided to confront whatever was causing these disturbances. I wish I had never opened that door.	reddit_ghoststories	\N	nightowl99	\N	2025-07-25 15:38:53.034829+00	\N
97cdda73-3122-41df-8aa5-8d824baac333	The Mirror in the Basement	When we moved into our new house, we found an old mirror in the basement. It was ornate and beautiful, but something about it felt wrong. My reflection seemed delayed, as if it was watching me before copying my movements. Sometimes I would catch glimpses of movement in the mirror when I wasn't even looking at it directly. The worst part was at night - I could swear I saw other faces looking back at me from within the glass. My family thought I was imagining things until my little sister started talking to "the lady in the mirror." That's when we knew we had to get rid of it, but the mirror had other plans.	ptt_marvel	\N	ghosthunter2021	\N	2025-07-25 15:38:53.034829+00	\N
\.


--
-- Data for Name: bronze_story_processing; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.bronze_story_processing (story_id, processing_status, processing_metadata, error_message, retry_count, created_at, updated_at) FROM stdin;
173113cd-bebf-4a96-bdb8-b833d7fa14ee	completed	{"language": "en", "quality_score": 1.0, "processing_cost": 0.001077100000000000000000, "chunks_generated": 2}	\N	0	2025-07-25 15:58:23.166446+00	2025-07-25 15:58:23.166446+00
d938dbbe-5542-4794-8dc6-3b23d6e9a55a	completed	{"language": "en", "quality_score": 1.0, "processing_cost": 0.001079200000000000000000, "chunks_generated": 2}	\N	0	2025-07-25 15:58:23.166446+00	2025-07-25 15:58:23.166446+00
97cdda73-3122-41df-8aa5-8d824baac333	completed	{"language": "en", "quality_score": 1.0, "processing_cost": 0.001081300000000000000000, "chunks_generated": 2}	\N	0	2025-07-25 15:58:23.166446+00	2025-07-25 15:58:23.166446+00
\.


--
-- Data for Name: silver_story_chunks; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.silver_story_chunks (id, story_id, chunk_text, chunk_context, chunk_order, chunk_type, overlap_start, overlap_end, content_embedding, search_embedding, chunk_length, chunk_word_count, semantic_keywords, embedding_model, embedding_version, embedding_model_version, processing_language, chunk_quality_score, embedding_cost, created_at) FROM stdin;
5b6d7f36-30a9-4e06-93f2-80c9ef27aaba	173113cd-bebf-4a96-bdb8-b833d7fa14ee	It was a dark and stormy night when I first encountered the ghostly presence in the old Victorian house. The floorboards creaked ominously as I climbed the stairs, and I could feel unseen eyes watching my every move. The temperature dropped suddenly, and my breath became visible in the frigid air. Then I heard it - a whisper so faint it could have been the wind, but the words were unmistakably cle	\N	0	narrative	0	0	\N	\N	400	72	\N	ollama_llama3.2	\N	\N	en	1	4e-05	2025-07-25 15:58:23.166446+00
b743e887-4e75-40fa-a984-e3789b53d4f8	173113cd-bebf-4a96-bdb8-b833d7fa14ee	ar: "Get out... before it's too late." I should have listened to that warning, but curiosity got the better of me. What I discovered in that attic changed my life forever.	\N	1	narrative	0	0	\N	\N	171	31	\N	ollama_llama3.2	\N	\N	en	1	1.71e-05	2025-07-25 15:58:23.166446+00
b97e64b3-83a2-4561-bfaa-d3f19629ae44	d938dbbe-5542-4794-8dc6-3b23d6e9a55a	Every night at exactly 3:33 AM, I would hear footsteps in the hallway outside my bedroom. At first, I thought it was just the house settling, but the pattern was too regular, too deliberate. The footsteps would start at the top of the stairs, slowly make their way down the hall, and stop right outside my door. I could see the shadow of feet blocking the light from under the door. But whenever I ga	\N	0	narrative	0	0	\N	\N	400	75	\N	ollama_llama3.2	\N	\N	en	1	4e-05	2025-07-25 15:58:23.166446+00
b3de7806-f95c-418d-a50f-d1567be73310	d938dbbe-5542-4794-8dc6-3b23d6e9a55a	thered the courage to look, there was nothing there. This went on for weeks until one night, I decided to confront whatever was causing these disturbances. I wish I had never opened that door.	\N	1	narrative	0	0	\N	\N	192	34	\N	ollama_llama3.2	\N	\N	en	1	1.92e-05	2025-07-25 15:58:23.166446+00
3b27b542-20f6-4f7a-82db-acdffb937fb1	97cdda73-3122-41df-8aa5-8d824baac333	When we moved into our new house, we found an old mirror in the basement. It was ornate and beautiful, but something about it felt wrong. My reflection seemed delayed, as if it was watching me before copying my movements. Sometimes I would catch glimpses of movement in the mirror when I wasn't even looking at it directly. The worst part was at night - I could swear I saw other faces looking back a	\N	0	narrative	0	0	\N	\N	400	75	\N	ollama_llama3.2	\N	\N	en	1	4e-05	2025-07-25 15:58:23.166446+00
9245fd7b-1188-4aee-a076-52b87ac785c2	97cdda73-3122-41df-8aa5-8d824baac333	t me from within the glass. My family thought I was imagining things until my little sister started talking to "the lady in the mirror." That's when we knew we had to get rid of it, but the mirror had other plans.	\N	1	narrative	0	0	\N	\N	213	42	\N	ollama_llama3.2	\N	\N	en	1	2.13e-05	2025-07-25 15:58:23.166446+00
\.


--
-- Name: bronze_stories bronze_stories_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bronze_stories
    ADD CONSTRAINT bronze_stories_pkey PRIMARY KEY (id);


--
-- Name: bronze_story_processing bronze_story_processing_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bronze_story_processing
    ADD CONSTRAINT bronze_story_processing_pkey PRIMARY KEY (story_id);


--
-- Name: silver_story_chunks silver_story_chunks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.silver_story_chunks
    ADD CONSTRAINT silver_story_chunks_pkey PRIMARY KEY (id);


--
-- Name: bronze_story_processing bronze_story_processing_story_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bronze_story_processing
    ADD CONSTRAINT bronze_story_processing_story_id_fkey FOREIGN KEY (story_id) REFERENCES public.bronze_stories(id);


--
-- Name: silver_story_chunks silver_story_chunks_story_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.silver_story_chunks
    ADD CONSTRAINT silver_story_chunks_story_id_fkey FOREIGN KEY (story_id) REFERENCES public.bronze_stories(id);


--
-- PostgreSQL database dump complete
--

