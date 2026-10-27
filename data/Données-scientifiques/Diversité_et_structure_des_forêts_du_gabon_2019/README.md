# Title of Dataset: A decade of diversity and forest structure: Post-logging patterns across life stages in an Afrotropical forest (Monts de Cristal selective logging 2019 vegetation census) 
---

## Abstract/Summary
Tropical forests are under threat of increasing pressure from income-generating land uses. Selective logging is a compromise that allows use of the land while leaving much of the forest canopy intact across a landscape. However, the ecological impacts of selective logging are unclear, with evidence of positive, negative, and negligible effects on forest structure and diversity. We examined the impact of selective logging on the structure and diversity of evergreen tropical forest in the Monts de Cristal region, a chain of mid-elevation hills in northwestern Gabon. For three size classes (seedling, sapling, and adult) of woody plant species, we tested whether forest structure (canopy openness, stem density, basal area, and relative liana abundances) and diversity were altered in forests that had been logged one year and ten years prior, compared to unlogged forest. In general, we found no large impact of selective logging treatment on the structure and diversity of adult woody plant communities, but the seedling and sapling communities were affected. Compared to unlogged forest, one- year post-logging forest had greater variation in canopy openness and lower sapling stem density. Ten-year post- logging forest had higher seedling and sapling species evenness, higher sapling species diversity, and higher relative abundance of sapling-sized lianas compared to unlogged forest. Our results show that key differences between intact and selectively logged forests persist in the understory at least a decade after logging. Overall, these results contribute an additional data point in the literature on selective logging, specifically representing the impacts of very low impact selective logging in Central African forests. Our study highlights the value of exploring selective logging impacts at multiple time periods of recovery, and makes an important contribution to the knowledge Central African managed forests. 


## Description of the data and file structure

### Description:
A. "plots-2019-census.csv' contains the vegetation plot information from the 80 vegetation plots: the plot number, date the plot was censused, which botanist performed plant ID in the plot, the subplot, species codes, diameter at breast height (DBH) in centimeters for sapling and adult trees, height in centimeters for seedlings, dbh height (if irregular), species
notes, information on main stem (for trees with multiple stems), and plot type 
- plot = plot number
- date = data plot was censused
- botanist = name of botanist that ID'd plants
- subplot = which subplot trees are in w/in plot
- spp = original species code ID
- spp2 = species code ID after herbarium identification/checking names in TNRS
- dbh = diameter at breast height in cm for trees
- height = height in cm for seedlings
- tag.no = tag number for each indiviual
- code = codes for different situations in field; L = liana, M = multi-stem, B = buttress roots, I = irregular measurement point, P or J = bent, with L or w/ L = DBH measured with liana around tree, X = broken
- dbh.height = height of dbh if moved up/down because measurement point was not possible at 1.3m from ground for any reason (see code for reason)
- main.stem = the largest stem of an individual
- plot.type = logging treatment plot is located in (controls separate)
- plot.type2 = logging treatment plot is located in (controls combined)


B. "habitat-2019-census.csv' contains the habitat information about the 80 vegetation plots: elevation, slope, plot type (i.e., which treatment each plot was in), and light measurements
- plot = plot number
- ele.max = maximum elevation in meters, from 9 measurements per plot
- ele.min = minimum elevation in meters, from 9 measurements per plot
- slope = ele.max-ele.min in meters
- plot.type = logging treatment plot is located in (controls separate)
- plot.type2 = logging treatment plot is located in (controls combined)
- light.mean = mean light levels per plot, from 9 densiometer readings per plot
- light.sd = standard deviation of light levels per plot, from 9 densiometer readings per plot
- elev.mean = mean evlevation per plot, from 9 measurements per plot
- elev.sd = standard deviation of light levels per plot, from 9 measurements per plot


### Data collection methods:
To assess the impact of selective logging on forest structure and diversity, we established a total of 80 vegetation plots between September 2018 and October 2019 (Fig. 1C). Each plot was 400 m2 in area (20 × 20 m). In order to capture the heterogeneous impact that selective logging can have on the forest, we randomly located 20 plots within each of three logging treatment areas: recently logged forest that had been logged approximately one year prior, older logged forest that had been logged ten years prior, and two unlogged forest areas. We measured two separate unlogged areas in order to try and capture some of the natural spatial variation in these forests. For all analyses, we considered the two unlogged areas as a single control treatment. We generated random point sampling schemes based on boundaries of yearly logging blocks using the sp package (Pebesma and Bivand, 2005, Bivand et al., 2013).
To sample the adult tree community, all free-standing woody stems ≥10 cm DBH were tagged, measured, and identified. For species that were difficult to identify in the field, we collected vouchers and depos- ited them at the National Herbarium (L’Herbier National du Gabon) who provided determinations for as many species as possible. We also tagged and measured climbing lianas ≥10 cm DBH following Gerwing et al. (2006), though we could not identify many individuals due to the limitations of collecting voucher specimens for lianas where leaves can only be found at the top of the canopy. To sample juvenile trees, saplings, and shrubs, we set up two subplots (10 × 10 m) nested within each plot.Within these subplots, we tagged, measured DBH, and identified all free- standing woody stems ≥1 cm and <10 cm DBH, and tagged and measured climbing lianas as above. For seedlings, we tagged, measured height, and identified all free-standing woody species and lianas ≥1 cm and ≤1 m in height in nine 1 × 1 m2 subplots at 9 points (at the four corners, center, and four middle points of each sides) within the main plot. We measured canopy openness at each of the 9 seedling subplots per plot, using a Spherical Crown Densiometer, Concave Model C (Forestry Suppliers, Jackson, MS, USA) (Lemmon, 1956) held level 1 m above the ground. Values were averaged to yield one canopy openness value for each adult tree plot.
To check for differences among treatments in topography, we measured elevation at each of the 9 seedling subplots per plot, using a Garmin GPSmap 64 s device (GARMIN, Olathe, KS, USA) and used the data to calculate slope and mean elevation values for each plot. Values were averaged to yield one elevation value for each adult tree plot. Plots had similar slope across all treatments (mean = 8 m, range = 1–26 m; Kruskal test, p = 0.16; Fig. A1B). Mean elevation was similar in older logged (505 m) and unlogged (503 m) forests (Dunn’s test, p-adjusted = 0.194), but was slightly higher in recently logged forests (531 m) compared to older logged and unlogged forests (Dunn’s test, p-adjusted < 0.001 and 0.0001, respectively; Fig. A1A). However, there was broad overlap in elevation values for all three treatments (ranges: older logged, ranges = 464–585 m in unlogged, 488–561 m in recently logged, and 451–654 m in older logged forest). To look at climate differences across sites, we used worldclim data (Fick and Hijmans, 2017) to consider differences in mean annual temperature and mean annual precipitation across sites (Table A2), and found that differences across treatments were small.




