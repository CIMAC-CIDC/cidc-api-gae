# Changelog

This Changelog tracks changes to this project. The notes below include a summary for each release, followed by details which contain one or more of the following tags:

- `added` for new features.
- `changed` for functionality and API changes.
- `deprecated` for soon-to-be removed features.
- `removed` for now removed features.
- `fixed` for any bug fixes.
- `security` in case of vulnerabilities.

## Version `0.27.28` - 20 Dec 2022

- `changed` schemas bump to remove ATACseq analysis batch report
- `removed` facets for the same
- `fixed` multifile handling, where it was set backwards

## Version `0.27.27` - 09 Dec 2022

- `changed` schemas bump for bug fix, new quality of sample option

## 07 Dec 2022

- `added` removal of assay_uploads and manifest_uploads along with rest of relational db in migration

## Version `0.27.26` - 02 Dec 2022

- `changed` schemas bump for updated ASSAY_TO_FILEPATH constant
- `changed` get GCS blob names to deduplicate across upload_types
- `changed` permissions handling to handle each trial instead of each trial / upload_type

## Version `0.27.25` - 01 Dec 2022

- `changed` schemas bump for dateparser version bump

## 01 Dec 2022

- `added` space handling to downloadable filelist.tsv url

## Version `0.27.24` - 30 Nov 2022

- `removed` references to permission system in cloud functions for biofx
- `removed` unused is_group option in granting permissions
  - was only used by the above now-removed permissioning system

## 29 Nov 2022

- `changed` all analysis files added to analysis ready facet and download

## Version `0.27.23` - 28 Nov 2022

- `changed` schemas bump for WES analysis template folder update

## 23 Nov 2022

- `fixed` plotly dash error on profile shipments dropdown

## Version `0.27.22` - 17 Nov 2022

- `changed` schemas bump wes new bait set swap

## 17 Nov 2022

- `fixed` wes_tumor_only_analysis dashboard counting

## 14 Nov 2022

- `removed` facets not used in the database or derived from current templates
- `added` facets missing from definitions that ARE used in the database
  - exclude metadata templates from facets/details

## Version `0.27.21` - 10 Nov 2022

- `changed` schemas bump for derive files returning None instead of error when no derivation is defined

## Version `0.27.20` - 08 Nov 2022

- `changed` schemas bumps for
  - adding batch to TCR meta csv
  - handling of clinical CSV files to strip any initial BOM
  - updated tumor-normal attempted pairing CSV

## Version `0.27.19` - 04 Nov 2022

- `fixed` WES TO counts also need to require a report
  - since tumor-normal pairing manifest schemas change
- `changed` how trial and network participants and samples are counted for
  - only count samples and participants that have associated assay data
  - does NOT affect assay-level counts for the Data Overview dashboard
  - DOES affect counts for Browse Data > Trial Table and Home Page
  
## Version `0.27.18` - 03 Nov 2022

- `changed` schemas bump for adding TCR meta csv

## 31 Oct 2022

- `changed` updated readme

## Version `0.27.17` - 31 Oct 2022

- `changed` only grant permissions on user reenable if they're approved

## Version `0.27.16` - 27 Oct 2022

- `changed` schemas bump for clinical data bug fix

## Version `0.27.15` - 27 Oct 2022

- `changed` schemas bump for clinical data bug fix

## Version `0.27.14` - 26 Oct 2022

- `changed` schemas bump for MIBI updates

## Version `0.27.13` - 25 Oct 2022

- `added` N/A organization for users

## Version `0.27.12` - 24 Oct 2022

- `changed` schemas bump for biofx pipeline integration updates

## Version `0.27.11` - 20 Oct 2022

- `changed` faceting for the previous microbiome and ctDNA analysis files

## Version `0.27.10` - 17 Oct 2022

- `fixed` reference to environment project name reference vs hard coded

## Version `0.27.9` - 17 Oct 2022

- `fixed` bug in building user permissions for files on the portal
  - allowed users with cross-assay permissions to see clinical data files
  
## Version `0.27.8` - 14 Oct 2022

- `added` credentialing to dataset update
- `fixed` project id bug

## Version `0.27.7` - 14 Oct 2022

- `added` protobuf package version for old generated code

## Version `0.27.6` - 13 Oct 2022

- `added` biquery permission delivery/revoking on role assignment

## Version `0.27.5` - 12 Oct 2022

- `changed` staging uploader role to temp replacement

## Version `0.27.4` - 10 Oct 2022

- `changed` schemas bump for MIBI support
- `added` facets for MIBI files

## Version `0.27.3` - 06 Oct 2022

- `fixed` bug in permissions application, where cross-trial permissions were used instead of cross-assay permissions

## Version `0.27.2` - 01 Oct 2022

- `added` PACT User role

## Version `0.27.1` - 16 Sep 2022

- `added` encryption for participant IDs via CSMS API

## Version `0.27.0` - 15 Sep 2022

- `removed` relational db code
- `changed` CSMS API to rely solely on JSON and schemas

## Version `0.26.31` - 14 Sep 2022

- `changed` schemas bump and migration for docs update / DM clean-up

## Version `0.26.30` - 31 Aug 2022

- `fixed` bug in credentials handling

## Version `0.26.29` - 31 Aug 2022

- `changed` credentials handling for generating signed urls
- `changed` default app run to debug False
- `added` user input sanitization when getting a specific template

## Version `0.26.28` - 17 Aug 2022

- `changed` bump schemas for microbiome metadata template changes and new shipping lab

## 16 Aug 2022

- `changed` edit H&E faceting to correctly label all new image uploads re allowing jpg files

## Version `0.26.27` - 15 Aug 2022

- `changed` bump schemas for ctdna analysis nulls and hande jpeg files
- `changed` issuing permissions for upload job actually gets them all now

## Version `0.26.26` - 11 Aug 2022

- `changed` cross-assay permissions to not include clinical data

## Version `0.26.25` -  9 Aug 2022

- `changed` schemas bump for hande manifest req relaxation

## Version `0.26.24` -  2 Aug 2022

- `changed` schemas bump for hande req relaxation

## Version `0.26.23` -  27 Jul 2022

- `changed` schemas bump for clinical data participant count fix

## Version `0.26.22` -  26 Jul 2022

- `changed` schemas bump for new participant alert on manifest upload

## 22 Jul 2022

- `changed` all WES analysis file purpose to "analysis"

## Version `0.26.21` -  13 Jul 2022

- `changed` schemas bump to fix requirements

## Version `0.26.20` -  13 Jul 2022

- `changed` schemas bump for WES template autogeneration tweaks
- `changed` schemas bump for WES analysis cnvkit to copynumber

## Version `0.26.19` -  12 Jul 2022

- `added` schemas bump, attach bytes to email for WES template autogeneration

## Version `0.26.18` -  8 Jul 2022

- `added` schemas bump, facets, counting for WES v3
- `added` migration to move old WES analysis
- `added` explicit migration for adding required for \_etag, \_created, \_updated
  - missing from `0.26.15` below
- `added` handling missing \_etag in bulk inserts for testing

## 30 Jun 2022

- `added` flask-cachecontrol to prevent caching of /users/data_access_report

## Version `0.26.17` - 21 Jun 2022

- `added` new wes bait set to relational db
- `added` catch for underlying psycopg2 error being thrown

## Version `0.26.16` - 21 Jun 2022

- `changed` schema version for addition of new wes bait set

## 14 Jun 2022

- `changed` reverted max download size from 1GiB to 100MB
  - with instance_class in app.yaml as F2, 512MB memory limit
  - testing on staging shows 100MB is likely functional limit for GAE-processed

## Version `0.26.15` - 13 Jun 2022

- `added` requirements for \_etag, \_created, \_updated
  - to prevent future 412 error on account reactivation
- `changed` schemas bump for shipping manifest requirement relaxing

## 13 Jun 2022

- `changed` compression for downloaded batches from gztar to zip
- `changed` max download size from 100MB to 1GiB

## Version `0.26.14` - 9 Jun 2022

- `changed` schemas bump for Microbiome support
- `added` facets, details, analysis counting for Microbiome

## Version `0.26.13` - 8 Jun 2022

- `changed` schemas bump for ctDNA support
- `added` facets, details, analysis counting for ctDNA

## Version `0.26.12` - 20 May 2022

- `changed` schemas bump to add ctDNA for assay_type in blood manifests
- `changed` WES counting again
- `added` clinical facets to the new downloadable_files endpoint
- `changed` copy to deepcopy for facet dict and add test to check all facets directly

## Version `0.26.11` - 19 May 2022

- `changed` order of user and url in single file download
- `changed` WES counting to reflect new system
- `added` new downloadable_files endpoint to return all facets grouped by assay
- `added` README.md as pypi long_description

## 6 May 2022

- `removed` `security` HSTS that was broken
- `added` missing facets for RNA MSI and Microbiome
- `changed` add more try/catch as result of tests; will be integrated on next bump

## 4 May 2022

- `added` `security` HSTS (headers) to prod and staging
  - [instructs browser to prefer `https`](https://cloud.google.com/appengine/docs/flexible/python/how-requests-are-handled#forcing_https_connections)

## Version `0.26.10` - 2 May 2022

- `changed` black, flask, werkzeug, jinja2, schemas version bumps
- `removed` typing_extensions dependency

## Version `0.26.9` - 21 Mar 2022

- `changed` schema version for wes-matching update

## Version `0.26.8` - 25 Mar 2022

- `changed` schema version to wes-matching to automate matching

## Version `0.26.7` - 25 Mar 2022

- `changed` schema version to peg regex to prevent errors

## Version `0.26.6` - 3 Mar 2022

- `changed` update schema dependency for miF schema preamble changes

## Version `0.26.5` - 9 Feb 2022

- `changed` alert email to new group cidc-alert@ds.dfci.harvard.edu

## Version `0.26.4` - 3 Feb 2022

- `changed` never return empty user email list, ie trials / uploads with no active users
- `changed` functions to reflect that iam=False option was never used

## Version `0.26.3` - 2 Feb 2022

- `fixed` don't return user emails for a trial / upload if that user is disabled

## Version `0.26.2` - 1 Feb 2022

- `added` function to return user emails for given trial_id / upload_type
- `fixed` pass session for when trial_id is None when building prefixes
- `added` group handling flag to granting/revoking permissions for BioFX group

## Version `0.26.1` - 31 Jan 2022

- `changed` schemas dependency for backwards compatible WES analysis

## Version `0.26.0` - 27 Jan 2022

- `removed` non-ACL based download permissions systems for production
- `removed` admin end point to trigger download permissions cloud function; trigger manually from GCP
- `changed` disabling inactive users to only return emails for newly disabled

## Version `0.25.68` - 24 Jan 2022

- `added` calls to revoke permissions when user is disabled, both manually and for inactivity

## Version `0.25.67` - 21 Jan 2022

- `fixed` point to new ACL-controlled bucket in ACL control functions

## Version `0.25.66` - 21 Jan 2022

- `added` name-based revoking functions for ACL equivalent to the granting ones
- `changed` other existing download permissions functions to use the ACL name-based equivalents
- `fixed` naming conventions that caused issues with cross-repo integration
- `added` more tests around ACL stuff

## Version `0.25.65` - 19 Jan 2022

- `added` string-based wrappers for ACL control instead of purely Blobs
- `added` function to return users allowed for a given trial id / upload type

## Version `0.25.64` - 18 Jan 2022

- `added` logging in ACL for non-specific KeyError

## Version `0.25.63` - 18 Jan 2022

- `added` storage client batching for ACL-based download permission granting/revoking

## Version `0.25.62` - 13 Jan 2022

- `changed` \*_all_download_permissions to \*_download_permissions, including endpoint address
- `added` upload_type kwarg to grant_download_permissions
- `added` trial_id and upload_type kwargs to revoke_download_permissions

## Version `0.25.61` - 12 Jan 2022

- `fixed` passed session to solve ACL-blocking KeyError

## Version `0.25.60` - 12 Jan 2022

- `fixed` `attempt` made grant_all_download_permissions mimic grant_iam_permissions
- `added` logging for with_default_session failures

## Version `0.25.59` - 10 Jan 2022

- `added` trial_id kwarg to grant_all_download_permissions

## Version `0.25.58` - 07 Jan 2022

- `changed` schema version bump to add comments to biofx analysis templates

## Version `0.25.57` - 06 Jan 2022

- `fixed` can't apply expiry condition to upload buckets as they are ACL-controlled

## Version `0.25.56` - 06 Jan 2022

- `fixed` typo by adding missing `and`

## Version `0.25.55` - 05 Jan 2022

- `added` back IAM download functionality for production environment only, partially reverting commit 7504926685dcd00b0c20b41911ec8aba7f8b98b0
- `change` version definition location from `setup.py` to `__init__.py` to match schemas/cli

## Version `0.25.54` - 22 Dec 2021

- `changed` admin grant all download permissions to run through cloud function

## Version `0.25.53` - 16 Dec 2021

- `removed` all IAM conditions on data bucket

## Version `0.25.52` - 15 Dec 2021

- `removed` all conditional IAM expressions on data bucket

## Version `0.25.51` - 15 Dec 2021

- `added` calls to ACL save, and smoketests
- `added` back calls for adding/removing lister permissions, and smoketests

## Version `0.25.50` - 14 Dec 2021

- `fixed` ACL syntax again; see https://googleapis.dev/python/storage/latest/acl.html#google.cloud.storage.acl.ACL

## Version `0.25.49` - 14 Dec 2021

- `fixed` ACL syntax
- `added` function to call to add permissions for particular upload job
- `removed` GOOGLE_DATA_BUCKET entirely from API

## Version `0.25.48` - 08 Dec 2021

- `add` error logging in Permission.insert

## Version `0.25.47` - 08 Dec 2021

- `remove` all gcloud client logic associated with download logic ie conditional IAM permissions
- `add` ACL gcloud client logic for downloads instead
- `remove` all lister permission as no longer needed with ACL instead of IAM
- `add` admin endpoint to call already existing function to grant all download permissions

## Version `0.25.46` - 30 Nov 2021

- `changed` schemas dependency (bump) for WES pipeline updates

## Version `0.25.45` - 23 Nov 2021

- `changed` schemas dependency for WES paired analysis comments field

## Version `0.25.44` - 22 Nov 2021

- `added` dry_run option for both CSMS insert functions

## Version `0.25.43` - 22 Nov 2021

- `added` conversion for CSMS value 'pbmc' for processed sample type
- `added` handling in shipments dashboard for no shipment assay_type

## Version `0.25.42` - 15 Nov 2021

- `fixed` correctly pass session in more places

## Version `0.25.41` - 15 Nov 2021

- `added` logging to see if `insert_manifest_into_blob` is called as expected

## Version `0.25.40` - 12 Nov 2021

- `fixed` bug in iterating offset in `csms.auth.get_with_paging`

## Version `0.25.39` - 12 Nov 2021

- `fixed` CSMS bug from chaining `detect_manifest_changes` and `insert_manifest_...`

## Version `0.25.38` - 11 Nov 2021

- `added` excluded property to CSMS test data and tests
  - `fixed` trying to add CSMS properties to CIDC entries
- `added` de-identified whole manifest from CSMS directly to test data
  - `fixed` reference to CIMAC ID in sample creation within models.templates.csms_api.insert_manifest_from_json()
  - `fixed` dict.items() is unhashable, so use dict.keys() to generate a set to check for _calc_difference()

## Version `0.25.37` - 08 Nov 2021

- `changed` bump schemas dependencies for mIF DM bug fix

## Version `0.25.36` - 08 Nov 2021

- `added` logging around error in CSMS testing (`deprecated`)

## Version `0.25.35` - 04 Nov 2021

- `changed` version for schemas dependency, for tweak to mIF template

## Version `0.25.34` - 03 Nov 2021

- `add` unstructured JSONB json_data column for shipments, participants, samples
- `add` copy of original JSON or CSMS data into json_data column
- `deprecated` non-critical columns in relational manifests, adding to json_data
- `add` correct exclusion of legacy CSMS manifests

## Version `0.25.33` - 29 Oct 2021

- `fixed` fix mIF excluded samples tab
- `fixed` fix typo 'errrors'

## Version `0.25.32` - 27 Oct 2021

- `added` subquery for counting ATACseq analysis to get_summaries for Data Overview dashboard

## Version `0.25.31` - 27 Oct 2021

- `changed` bump schemas version for ATACseq analysis updates

## Version `0.25.30` - 27 Oct 2021

- `fixed` set os environ TZ = UTC before datetime is imported every time

## Version `0.25.29` - 26 Oct 2021

- `fixed` correctly pass session throughout models/templates/csms_api

## Version `0.25.28` - 26 Oct 2021

- `remove` incorrect accessing of CSMS manifest protocol_identifier which is only stored on the samples

## Version `0.25.27` - 25 Oct 2021

- `added` facets and file details for mIF report file
- `remove` Templates facet entirely

## Version `0.25.26` - 22 Oct 2021

- `fixed` second call to get_with_authorization again

## Version `0.25.25` - 22 Oct 2021

- `fixed` second call to get_with_authorization

## Version `0.25.24` - 22 Oct 2021

- `changed` schemas bump for mIF QC report

## Version `0.25.23` - 21 Oct 2021

- `changed` moved validation of trial's existing in the JSON blobs to better reflect name and usage

## Version `0.25.22` - 21 Oct 2021

- `fixed` pass limit and offset as params instead of kwargs to requests.get

## Version `0.25.21` - 19 Oct 2021

- `added` handling to remove old-style permissions

## Version `0.25.20` - 19 Oct 2021

- `added` logging to set_iam_policy errors

## Version `0.25.19` - 15 Oct 2021

- `changed` CSMS_BASE_URL and CSMS_TOKEN_URL to be pulled from secrets

## Version `0.25.18` - 14 Oct 2021

- `fixed` changed prefix generator to correctly handle prefixes without regex support

## Version `0.25.17` - 13 Oct 2021

- `changed` GCP permissions from single conditions to multi-conditions using || and && operators
- `changed` expiring permission to be on the general CIDC Lister role instead of every startsWith condition separately

## Version `0.25.16` - 07 Oct 2021

- `added` function for finding CSMS changes and getting updates for relational db
- `added` function to execute corresponding updates to JSON blob from CSMS changes

## Version `0.25.15` - 04 Oct 2021

- `added` grant_lister_access and revoke_lister_access for custom role CIDC Lister that is required for all downloads

## Version `0.25.14` - 24  Sept 2021

- `added` API endpoint to add a new manifest given JSON from CSMS

## Version `0.25.13` - 23 Sept 2021

- `added` added TWIST enum values to WES in relational tables

## Version `0.25.12` - 23 Sept 2021

- `added` schemas bump to add TWIST enum values to WES in JSON

## Version `0.25.11` - 22 Sept 2021

- `added` module export for models.templates

## Version `0.25.10` - 22 Sept 2021

- `changed` schemas bump to add TCRseq controls

## Version `0.25.9` - 22 Sept 2021

- `changed` schemas bump for new TCRseq Adaptive template

## Version `0.25.8` - 08 Sept 2021

### Summary

Initial set up of tables and definition of needed classes for base metadata and assay uploads. Generated new-style templates and added full testing data for pbmc, tissue_slide, h_and_e, wes_<fastq/bam>; demo for clinical_data. Implemented JSON -> Relational sync function and wired for testing. Added relational hooks into existing manifest and assay/analysis uploads. Added way to trigger initial synchronization. Allows relational ClinicalTrials to be edited along with TrialMetadatas from the admin panel.

### Details

- `added` JIRA integration ([#564](https://github.com/CIMAC-CIDC/cidc-api-gae/pull/564))
- `added` `changed` Step 1 of Relational DB towards CSMS Integration ([#549](https://github.com/CIMAC-CIDC/cidc-api-gae/pull/549/))
- `added` Add logging to syncall_from_blobs ([#565](https://github.com/CIMAC-CIDC/cidc-api-gae/pull/565))
- `added` Add admin controls for relational Clinical Trials ([#567](https://github.com/CIMAC-CIDC/cidc-api-gae/pull/567))
- `fixed` Some perfecting tweaks ([#568](https://github.com/CIMAC-CIDC/cidc-api-gae/pull/568))
- `fixed` Make sure that new templates are identical to old ones ([#569](https://github.com/CIMAC-CIDC/cidc-api-gae/pull/569))
- `added` Add some safety and flexibility to reading ([#570](https://github.com/CIMAC-CIDC/cidc-api-gae/pull/570))
- `fixed` Fix header check; add better error handling and tests ([#571](https://github.com/CIMAC-CIDC/cidc-api-gae/pull/571))
- `added` Add 5 new optional columns to PBMC manifest for TCRseq ([#572](https://github.com/CIMAC-CIDC/cidc-api-gae/pull/572))
