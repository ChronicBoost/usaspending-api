FORMAT: 1A
HOST: https://api.usaspending.gov

# Count of CFDA Receiving Disaster/Emergency Funding [/api/v2/disaster/cfda/count/]

This endpoint provides the count of CFDA programs which received disaster/emergency funding per the requested filters.

## POST

This endpoint returns a count of CFDA programs

+ Request (application/json)
    + Schema

            {
                "$schema": "http://json-schema.org/draft-04/schema#",
                "type": "object"
            }

    + Attributes
        + `filter` (required, Filter, fixed-type)

    + Body

            {
                "filter": {
                    "def_codes": ["L", "M", "N"]
                }
            }

+ Response 200 (application/json)
    + Attributes (object)
        + `count` (required, number)
    + Body

            {
                "count": 5
            }

# Data Structures

## Filter (object)
+ `def_codes` (required, array[DEFC], fixed-type)
+ `award_type_codes` (optional, array[AssistanceTypeCodes], fixed-type)
    Defaults to all Assistance Type Codes. Applicable only when requested `award` spending.

## DEFC (enum[string])
List of Disaster Emergency Fund (DEF) Codes (DEFC) defined by legislation at the time of writing

### Members
+ `A`
+ `B`
+ `C`
+ `D`
+ `E`
+ `F`
+ `G`
+ `H`
+ `I`
+ `J`
+ `K`
+ `L`
+ `M`
+ `N`
+ `O`
+ `P`
+ `Q`
+ `R`
+ `S`
+ `T`
+ `9`

## AssistanceTypeCodes (enum[string])
List of assistance award type codes supported by USAspending.gov

### Members
+ `02`
+ `03`
+ `04`
+ `05`
+ `06`
+ `07`
+ `08`
+ `09`
+ `10`
+ `11`
