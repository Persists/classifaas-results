#### Slide 1: Title Slide

Welcome everyone. Today I am presenting my Master Thesis titled 'Exploring the Effects of Hardware Heterogeneity on FaaS Performance Variability.' My name is Jonas as you might know already.

#### Slide 2: Motivation - The gap between the "Serverless" promise and the physical reality.

- I will focus on the core promise of FaaS is abstraction.
  - it promisses developers focusing on writing code rather worrying about the underlying infrastructure, and its management.
  - Developers only specify abstract resource requirements of their functions, like memory size.
  - The platform automatically handles resource allocation, and scaling of function instances that serve incoming requests.
- In reality identical functions with the same configuration still exhibit significant performance variability.
- Because FaaS uses pay-per-use billing, this performance variance directly translates into cost variance
- The Hypothesis, this Thesis explores is that hardware heterogeneity is a significant driver of this performance variability.
- Meaning that a function performs differently depending on the physical hardware it is assigned to, which the user dont have control over.
- Specifically, we investigate CPU heterogeneity, as CPUs are a critical resource for compute-intensive workloads common in FaaS applications.
- To adress this we designed a benchmarking framework

#### Slide 3: Benchmark Design

- I will now introduce the benchmark design we used to explore hardware heterogeneity effects

- The architecture consists of three main components:

  - The deployment module, that automates the deployment of FaaS functions across multiple cloud providers.
  - Generally Deploys functions consisting of a synthetic microbenchmark and a instrumentation wrapper, that collects hardware information at runtime.

  - In additionw we employ a decoupled load generator that generates Load by invoking the deployed functions according to a closed workload model.
  - the decoupling allows us to perform subequent runs over long periods of time without redeploying functions.

- As we wont to adress hardware hetereogenity, we aim to maximize the benchmark's exposure to different hardware.
- The problem, platforms keep function instances warm for subsequent invocations,
  -> meaning that once a fnction instance is created on a hardware, subsequent invocations will be served by the same instance on the same hardware.
- To adress this we used three different strategies to trigger new instance creation:
  - high concurrency -> invoking the same function many times in parallel forcing the platform to scale out insetances.
  - sequential execution -> executing multiple sequential benchmark runs with delays in between that trigger the cloud provider to recycle instances.
  - forced instance recycling -> Purposely crash a function instance after a sufficient number of invocations to force the platform to create a new instance potentially on different hardware.

#### Slide 4: CPU identification across platforms

- Before starting with the experimental results, its important to understand how we identify different cpu models across platforms.
- Important practical challenge: platforms abstract CPU identity differently
- To extract CPU identity information, we relied on the information from the /proc/cpuinfo file - which is commonly available on linux based systems.
  - While Azure gives the full CPU model name, AWS and alibaba only give generic names, like intel xeon 2.5 ghz and gcp fully sets the name to unknown.
  - however for gcp we can make use of the model number to differentiate between cpu models.
- Even with these constraints, we still were able to observe different cpu models on all platforms, enabling us to study its effect.

6min

#### Slide 5: Experimental design overview 3 stages

- To adress multiple dimensions of hardware heterogeneity effects, we designed a three stage experimental design.
- First of all we have some common setup accross all experiments:

  - Every microbenchmark is executed with a fixed problem size across all providers, regions and configurations to ensure comparability.
  - We chose our concurrency level and total number, so we have multiple invocations per instance.
  - We aim each instance to serve 4 invocations
  - For the analysis:
    - discard the first invocation to avoid cold start effects.
    - we only keep instances where all 4 invocations succeeded

- Stage A builds the regional baseline

  - if hardware hetereogenity existis across regions
  - we see if this hetereogenity correleates with performance and its variability
  - We deploy a Matrix Multiplication benchmark across 12 region per provider using 1 configuration

- Stage B asesses whether memory configuration changes CPU assignment and whether variability narrows or shifts.
- 1 region from stage A with multiple cpus per provider

- The final stage C analyzes the temporal dynamics of CPU assignment and performance and also taking a look at different microbenchmarks.
- We use this stage also for a deeper statistical analysis as it generates the largest data set.

- In all stages we carefully time experiment runs to account for temporal performance patterns.

#### Slide 6: Stage A Gcp results

- One Experiment run consists of a fixed number of total requests, and a concurrency level
- the results show the results of one experiment run per region

- What makes gcp interesting: highest amount of different cpu models
- rightmost panel cpu composition per region - stacked bar plot
- left mean performance per region
- middle coefficient of variation per region
- high variability in performance across regions (25%)
- All providers: more spread cpu composition regions also yield higher variability (middle coefficient of variation plot)

#### Slide 7: Stage A: Azure results

- variation high for some regions and for some very low, thats a problem we will adress later
- AMD 9V74 regions always slower than Intel regions

#### Slide 8: Stage A: AWS results

- Finall ecdf plot for all providers
- Each line presents a cpu model in a region, same color means same cpu model
- All except alibaba cpu models group together quite well
- still some variability within same cpu model
  - maybe due to noisy neighbors or other region specific factors
- Interesting, in AZURE the models group best together -> maybe due to the highest resolution in cpu identification

#### Slide 9: Stage B: Memory configuration effects

- make it fast
- we ran the same matrix multiplication benchmark across different memory configurations
- like on the first plot it shows a stacked bar plot with each color being the cpu sahre and how it behaves
- the hardware assignment doesnt change with memory configuration !for all providers
- For azure there is no 128mb configuration -> missing bar

#### Slide 10: Stage B, Performance deviaton across memory configurations

- Chart shows how the different cpu models perfomance deviate from the overall mean per memory configuration
- lower means faster, higher means slower
- every platform except alibaba the difference decreases with higher memory configuration
- on gcp, aws and alibaba cloud differences up to 50%
- Azure only 30% difference, stays verly consistent only with small decrease

#### Slide 11: Stage C: Temporal CPU composition overview

- Only Aws is depicted here, has most interesting cpu composition over time
- composition over one week, with 4 experiment runs per day
- shows the avg cpu composition over all benchmarks per time slot
  - we did them sequentially with small delays in random order to avoid bias
- aws main cpu the intel cpu has the highest share overall (its also the slowest cpu)
- the other cpus are sometimes more dominant in certain time slots (6:00 and 12:00 local time) and during the weekend

- Other providers are really stable over time in the cpu composition

- interesting, we didnt observe amd cpu in stage A, we did 7:15 local time at thursday in november

#### Slide 12: Stage C: Decomposition of performance variability

- Finally we also performed a variance decomposition analysis
- There fore we use type 2 Anova.
- Decomposition: allows us to quantify how much of the total variability can be explained by hardware heterogeneity
- The chart shows the results for all providers and benchmarks
- The blue bars show the portion of variability explained by cpu model
- The green bars show the portion explained by time
- The red shows the residual variability that cant be explained by these two factors

- GCP and AWS are most affected by cpu model
- Alibaba is most affected by the time
- Azure has the lowest impact of cpu model on its performance variability, meaning the highest residual variability

- that can be adressed to the factor we will address in the last slide

#### Slide 15: Stage B heatmap (this slide maybe out of time)

- final plot for stage b
- shows heatmap of coefficent of variation - per memory and cpu model for each platform
- aws shows the smallest intra cpu model variability accross memory configurations
- overall variability of gcp and aws is farly the same (sorry for the numbers which are hard to read)
- interesting significant cv for azure for the 512mb configuration on all cpu models - we will adress this in the last slide
