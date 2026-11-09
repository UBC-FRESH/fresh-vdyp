# VDYP7 coefficient and control map

Date: 2026-11-09
Status: observed structure, equation forms still partly unresolved

## Why this file exists

The VDYP coefficient files are numeric tables. The control file supplies the
model-step mapping, but the exact equation form for every family is not always
written in the bundle. This note records what is known and what must be
validated before a Python equation is promoted.

## Control sequence examples

From `VDYP.CTR`:

```text
090  coe\VTOTREG4.coe     total whole-stem volume
091  coe\regvu.coe        utilization volume
092  coe\regvcu.coe       close-utilization volume
093  coe\regvdu.coe       volume net of decay
094  coe\regvwu.coe       volume net of decay and waste
095  coe\regbreak.coe     breakage
050  coe\regyhlp.coe      height, primary species
051  coe\regyhlpa.coe     height, primary species
052  coe\regyhlpb.dat     height, primary species
053  coe\reghl.coe        height, non-primary species
148  coe\basp05.coe       BA growth, primary species
149  coe\basp06.coe       BA growth, non-primary species
150  coe\dqsp05.coe       DQ growth, primary species
151  coe\dqsp06.coe       DQ growth, non-primary species
106  coe\YLDBA407.coe     BA yield, primary layer
107  coe\YLDDQ45.coe      DQ yield, primary layer
```

## Observed family shapes

### Whole-stem volume

`VTOTREG4.COE` has 74 rows. A row starts with a curve group number followed by
nine numeric coefficients. The public model overview identifies whole-stem
volume as a static yield model added after the stand projection.

Unknowns:

- exact variable order in the nine coefficient columns;
- which terms are log-transformed;
- species/BEC grouping rules.

### Utilization and close-utilization volume

`REGVU.COE` and `REGVCU.COE` have 292 rows each. Rows begin with a group and a
species index, followed by four or three coefficients. The public overview
identifies these as reduction models applied after whole-stem volume.

Unknowns:

- exact equation form;
- group and species index semantics;
- decay/waste interaction with `REGVDU` and `REGVWU`.

### Height / Lorey height

`REGHL.COE` has 302 rows. Rows contain species, BEC, coastal/interior indicator,
and two coefficients. This is one of the easier families to map and validate.

Unknowns:

- exact predictor variables;
- BEC and species interactions;
- whether the coefficient pair is a base/exponent or intercept/slope.

### Basal-area increment

`REGBA25.COE` has 126 rows. Rows contain species/BEC, coefficient labels
`A0`...`A8`, a flag, and a coefficient vector. `BASP05.COE` and `BASP06.COE`
are smaller species-specific BA growth files.

Unknowns:

- exact design matrix;
- the meaning of the `A0`...`A8` labels and flag;
- interaction with `YLDBA407` and `YLDBA309`.

### Diameter increment

`DQSP05.COE` and `DQSP06.COE` are small species-specific DQ growth files.
`REGDQ18`, `REGDQ24`, `REGDQ26`, `REGDQI04`, and `REGDQL2` are related
constraint and increment files.

Unknowns:

- exact equation form;
- constraint interactions.

### Yield tables

`YLDBA407.COE` and `YLDDQ45.COE` are yield-table helpers. `VDYP.tcl` defines the
output columns.

## What the bundle gives us

- the coefficient values;
- the control-sequence mapping;
- species and BEC definitions;
- the console oracle;
- the output schema.

## What the bundle does not fully give us

- a human-readable equation for every family;
- the meaning of every coefficient column;
- the design-matrix construction for every increment model.

## How to resolve the gaps

1. Read the public overview and console guide for model structure.
2. Use `VDYP7Console` as an oracle with controlled inputs.
3. Vary one input at a time and isolate the family response.
4. Compare candidate equation forms against golden outputs.
5. Decompile only the specific routine whose form cannot be inferred.
6. Record the equation, coefficient mapping, and validation evidence before
   promoting a family.

## Family promotion order

```text
1. REGHL height / Lorey height
2. VTOTREG4 whole-stem volume
3. REGVCU close-utilization volume
4. REGVU utilization volume
5. REGVDU / REGVWU decay and waste
6. REGBA25 / BASP05 / BASP06 BA increment
7. DQSP05 / DQSP06 DQ increment
8. YLDBA407 / YLDDQ45 yield helpers
```

The order is chosen to build from simple static equations toward interacting
increment models.

## Non-negotiable rule

A family without a documented equation and a console validation case is
`experimental` or `not_implemented`. It is never silently filled with a guess.
