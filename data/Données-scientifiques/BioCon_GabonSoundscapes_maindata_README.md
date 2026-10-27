# Data for: Impacts of logging, hunting, and conservation on vocalizing biodiversity in Gabon

Dataset DOI: [10.5061/dryad.4tmpg4frs](https://doi.org/10.5061/dryad.4tmpg4frs)

## Description of the data and file structure

Between February 2021 and June 2022, we sampled soundscapes at 110 sites across Gabon. Our sampling covered the main dry (May to September; 37 sites) and rainy season (October to April; 73 sites). We sampled soundscapes in four of Gabon's nine provinces: the Ogooué-Ivindo, Ogooué-Lolo, Nyanga, and Ngounié. In each province, we sampled three different land use designations: national parks (Ivindo, Lopé, and Moukalaba-Doudou National Parks, 41 sites total), FSC-certified selective logging concessions (anonymized, 32 sites in 3 concessions), non-certified selective logging concessions (anonymized, 32 sites in 3 concessions). Additionally, we sampled in a proposed community conserved area, Ibola Dja Bana Ba Massaha, in the Ogooué-Ivindo province (5 sites, hereafter referred to as the PCCA). The sites sampled in the PCCA were in an unlogged area of forest situated within a non-certified concession. During our study, the legal status and designation of this land were being determined.

Our sites included two main habitat types present in our study area: closed rainforest (hereafter referred to as ‘forest’), and forest-savannah mosaic (‘mosaic’). Sampling sites within the mosaic were situated within forest patches at least 200 m from the forest edge. 

We deployed bioacoustic recorders to quantify the soundscape within each forest designation, separating sampling sites by at least 1 km to ensure independence. At each site, we deployed one Bioacoustic Recorder (BAR-LT, Frontier Labs) at 1.8 m above ground with a single omnidirectional microphone pointing down, as a compromise between limiting exposure to rain and capturing a broader array of sounds. Recorders were programmed for continuous, autonomous recording in 30 min segments for at least seven days per site. We only included complete days in this dataset (e.g. 1440 min per day; mean no. days per site = 5.8 ± 2.0). We recorded soundscapes at 40 dB gain and 44.1 kHz sample rate.

For each site, we quantified logging disturbance and hunting pressure. We measured changes in the forest due to selective logging in three ways. First, we calculated forest extent within a 300m buffer around our sites. Second, we documented the logging history at each site as specified in forest management maps and logging crews as years since loggin&#x67;*.* These were aggregated into three categories  (logged <2 years ago, logged 20+ years ago, never logged). Third, we calculated mean canopy height at 100, 300, and 500 m buffers as a measure of forest quality. See corresponding paper for more details.

Hunting pressure was calculated in two ways. First, we quantified the number of gunshot sounds detected at each site during the recording period. Secondly, we produced a spatially explicit accessibility layer to estimate the spatial variability in hunting effort. Variables included slope, distance to settlements, rivers, and roads. The final metric (Access) was scaled and inverted so the resulting metric is unitless, where the higher the relative accessibility the more accessible the sites. See corresponding paper for more details.

We calculated two acoustic indices: (i) Power Minus Noise (ToTPMN) and (ii) Soundscape Saturation (sat1db). These were calculated for 256 frequency bins between 0 and 11 kHz (~43 Hz bandwidth each).  See corresponding paper for more details.

### Files and variables

#### File: BioCon_GabonSoundscapes_maindata.csv

**Description:** 

##### Variables

* SiteRename: Site ID
* ForestUse: Forest designation including National parks, proposed conservation area, and different logging concession types
* ForestType: Forest type, closed rainforest (forest) or forest-savannah mosaic (mosaic)
* Year: Year of recording
* DeployDateMMDDYY: Date the bioacoustic detector was deployed
* Date: Date of the recording
* Time: Time of the recording
* DatetimeFinal: Date and time of the recording
* MinSinMid: Minute since midnight, calculated from time
* Season: Dry season or rainy season
* Altitude: Altitude (m)
* Slope: Slope derived from a 30m digital elevation model ([Farr et al., 2007](https://www.sciencedirect.com/science/article/pii/S000632072400288X#bb0225)) (m)
* DistVillage: Distance to nearest settlement retrieved from OpenStreetMap (2022) (m)
* DistRoads: Distance to nearest road retrieved from OpenStreetMap (2022) (m). We excluded roads no longer operational
* DistWater: Distance to nearest river retrieved from OpenStreetMap (2022) (m). We excluded rivers not suitable for navigation
* Gun_RawGunshots: Count of gunshots detected at the site
* Gun_DailyGunshots: Mean daily gunshot rate 
* CH_100m: Mean forest canopy height within a 100m buffer of the site (m)
* CH_300m: Mean forest canopy height within a 300m buffer of the site (m)
* CH_500m: Mean forest canopy height within a 500m buffer of the site (m)
* Avg_canopy: Average canopy cover calcuated from 4 samples (No cover 0-1 closed cover)
* sd_canopy: Standard deviation in canopy cover calcuated from 4 samples (No cover 0-1 closed cover)
* FC_Final_300m: Forest extent within a 300m buffer of the site (No forest 0-1 complete forest)
* YearsSinceLogging_cat: Categorical variable of logging history
* Access: Accessibility layer calculated from Slope, DistVillage, DistWater, and DistRoad. The higher the relative accessibility the more accessible the sites
* sat1db: Soundscape saturation (%) at a threshold of 1.5db
* TotPMN: Power minus noise (dB), i.e. total energy of sound above background noise

## Access information

Data was derived from the following sources:

* *HOTOSM Gabon populated places*. [https://data.humdata.org/dataset/hotosm_gab_populated_places](https://data.humdata.org/dataset/hotosm_gab_populated_places) (2022)
* Humanitarian OpenStreetMap Team. *HOTOSM Gabon roads*. [https://data.humdata.org/dataset/hotosm_gab_roads](https://data.humdata.org/dataset/hotosm_gab_roads) (2022)
* Humanitarian OpenStreetMap Team. *HOTOSM Gabon waterways.&#xA0;*[https://data.humdata.org/dataset/hotosm_gab_waterways](https://data.humdata.org/dataset/hotosm_gab_waterways) (2022)
* T.G. Farr, P.A. Rosen, E. Caro, R. Crippen, R. Duren, S. Hensley, M. Kobrick, M. Paller, E. Rodriguez, L. Roth, D. Seal, S. Shaffer, J. Shimada, J. Umland, M. Werner, M. Oskin, D. Burbank, D. Alsdorf. The shuttle radar topography Mission. Rev. Geophys., 45 (2) (2007), [10.1029/2005RG000183](https://doi.org/10.1029/2005RG000183)
* R. Dubayah, J.B. Blair, S. Goetz, L. Fatoyinbo, M. Hansen, S. Healey, M. Hofton, G. Hurtt, J. Kellner, S. Luthcke, J. Armston, H. Tang, L. Duncanson, S. Hancock, P. Jantz, S. Marselis, P.L. Patterson, W. Qi, C. Silva. The global ecosystem dynamics investigation: high-resolution laser ranging of the Earth’s forests and topography. Science of Remote Sensing, 1 (2020), Article 100002, [10.1016/j.srs.2020.100002](https://doi.org/10.1016/j.srs.2020.100002)

  <br />

