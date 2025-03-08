# Flare x Google Cloud Verifiable AI Hackathon - RAG Track 🚀

## Quick Links
- [Hackathon Homepage](https://hackathon.flare.network)
- [RAG Template Repository](https://github.com/flare-foundation/flare-ai-rag)
- [Developer Hub](https://dev.flare.network/intro/)
- [Hackathon Onboarding Guide](https://dev.flare.network/hackathon/onboarding/)

## RAG Track Details
- **Prize Pool**: 
  - OnSite Prize: $15,000
  - Virtual Prize: $8,000
- **Track Goal**: Build a specialized Retrieval-Augmented Generation (RAG) system for Flare ecosystem content

## Important Dates
### Virtual Track Timeline
- Registration Period: Feb 3 - March 6
- Hackathon Period: March 7-14
- Project Submission: March 14
- Winners Announcement: March 31

## Technical Resources

### About Flare
Flare is the blockchain for data ☀️, offering:
- Secure, decentralized access to high-integrity data
- EVM-compatible smart contract platform
- Optimized for decentralized data acquisition
- Support for price and time-series data
- Blockchain event and state data
- Web2 API data integration

### Required Setup
1. **Google Cloud Access**
   - Project: `verifiable-ai-hackathon`
   - Access granted: March 6th

2. **API Keys Required**
   - Gemini API Key (Required)
   - OpenRouter API Key (Optional)

3. **Development Environment**
   - Python with uv package manager
   - Docker
   - Git

### Core Components
1. **Vector Database**: Qdrant
2. **LLM Integration**: Google Gemini
3. **Data Processing**: Pandas
4. **API Framework**: FastAPI
5. **Frontend**: React-based chat UI

## Technical Setup Requirements

### Google Cloud Setup
1. **Google Account Access**:
   - Access to `verifiable-ai-hackathon` project (granted March 6th)
   - Must use registered Google account email

2. **API Credentials**:
   ```bash
   # Required Environment Variables
   GEMINI_API_KEY=<your-key>
   TEE_IMAGE_REFERENCE=ghcr.io/YOUR_REPO_IMAGE:main
   INSTANCE_NAME=PROJECT_NAME-TEAM_NAME
   ```

3. **gcloud CLI Setup**:
   ```bash
   # Verify installation
   gcloud version

   # Authentication
   gcloud auth login

   # Verify project access
   gcloud projects list
   ```

### Development Tools
1. **Required Software**:
   - git
   - uv (Python package manager)
   - Docker
   - gcloud CLI

2. **Environment Setup**:
   ```bash
   # Source environment variables
   source .env
   ```

## Confidential Computing Setup

### AMD SEV Deployment
```bash
gcloud compute instances create $INSTANCE_NAME \
  --project=verifiable-ai-hackathon \
  --zone=us-central1-c \
  --machine-type=n2d-standard-2 \
  --network-interface=network-tier=PREMIUM,nic-type=GVNIC,stack-type=IPV4_ONLY,subnet=default \
  --metadata=tee-image-reference=$TEE_IMAGE_REFERENCE,tee-container-log-redirect=true \
  --maintenance-policy=MIGRATE \
  --provisioning-model=STANDARD \
  --service-account=[email protected] \
  --scopes=https://www.googleapis.com/auth/cloud-platform \
  --min-cpu-platform="AMD Milan" \
  --tags=flare-ai,http-server,https-server \
  --create-disk=auto-delete=yes,boot=yes,device-name=$INSTANCE_NAME,\
  image=projects/confidential-space-images/global/images/confidential-space-debug-250100,\
  mode=rw,size=11,type=pd-standard \
  --shielded-secure-boot \
  --shielded-vtpm \
  --shielded-integrity-monitoring \
  --reservation-affinity=any \
  --confidential-compute-type=SEV
```

### Intel TDX Deployment
```bash
gcloud compute instances create $INSTANCE_NAME \
  --project=verifiable-ai-hackathon \
  --zone=us-central1-a \
  --machine-type=c3-standard-4 \
  --network-interface=network-tier=PREMIUM,nic-type=GVNIC,stack-type=IPV4_ONLY,subnet=default \
  --metadata=tee-image-reference=$TEE_IMAGE_REFERENCE,tee-container-log-redirect=true \
  --maintenance-policy=TERMINATE \
  --provisioning-model=STANDARD \
  --service-account=[email protected] \
  --scopes=https://www.googleapis.com/auth/cloud-platform \
  --tags=flare-ai,http-server,https-server \
  --create-disk=auto-delete=yes,boot=yes,device-name=$INSTANCE_NAME,\
  image=projects/confidential-space-images/global/images/confidential-space-debug-0-tdxpreview-c38b622,\
  mode=rw,size=11,type=pd-balanced \
  --shielded-secure-boot \
  --shielded-vtpm \
  --shielded-integrity-monitoring \
  --reservation-affinity=any \
  --confidential-compute-type=TDX
```

## VM Management

### Instance Operations
```bash
# Stop VM
gcloud compute instances stop $INSTANCE_NAME

# Start VM
gcloud compute instances start $INSTANCE_NAME

# View logs
gcloud logging read "resource.type=gce_instance AND resource.labels.instance_id=YOUR_INSTANCE_ID" --project=verifiable-ai-hackathon
```

### Important Considerations
1. **VM Monitoring**:
   - Instances are continuously monitored
   - Use only for hackathon purposes
   - Misuse leads to termination and possible ban

2. **Troubleshooting**:
   - For Gemini API issues:
     - Verify Google account
     - Wait 5-10 minutes after access
     - Try incognito mode
   - For gcloud CLI issues:
     - Use `--no-launch-browser` flag
     - Check multiple account conflicts
   - For Windows:
     - Use git BASH for Linux commands
   - For multiple projects:
     ```bash
     gcloud config set project verifiable-ai-hackathon
     gcloud auth application-default set-quota-project verifiable-ai-hackathon
     ```

3. **Support Protocol**:
   When seeking help, provide:
   - Team name
   - VM instance name
   - Error screenshots
   - Steps attempted

## Judging Criteria
Judges include:
- Hugo Philion (Co-Founder of Flare & CEO of Flare Labs)
- Ross Nicoll (Google Cloud)
- Filip Koprivec (Head of Developer Relations)
- Dinesh Pinto (Technical Product Lead)
- Horia Magureanu (Research Scientist)

## Support Resources
- Telegram Support Group: [https://t.me/+StI5VEIvtIg2ODlh](https://t.me/+StI5VEIvtIg2ODlh)
- Email Support: [email protected]

## Project Structure
```
flare-ai-rag/
├── chat-ui/          # React-based frontend
├── src/
│   ├── data/         # Training data and resources
│   └── flare_ai_rag/ # Core RAG implementation
├── tests/            # Test suite
└── docker/           # Docker configuration
```

## Key Files to Note
- `.env` - Configuration for API keys and settings
- `pyproject.toml` - Python dependencies
- `Dockerfile` - Container configuration
- `supervisord.conf` - Process management
- `nginx.conf` - Web server configuration

## Getting Started Steps
1. Clone the template repository
2. Set up API keys in `.env`
3. Install dependencies using uv
4. Build and run Docker container
5. Access the UI at localhost:8080

## Best Practices
1. Use version control effectively
2. Write comprehensive tests
3. Document your code
4. Follow Python best practices
5. Implement proper error handling
6. Consider scalability
7. Focus on user experience

## Data Sources
- Flare documentation
- Technical whitepapers
- API documentation
- Community resources
- Governance proposals

## Security Considerations
1. API key management
2. Data validation
3. Rate limiting
4. Error handling
5. Input sanitization

## Evaluation Metrics
1. Technical implementation
2. Innovation
3. User experience
4. Code quality
5. Documentation
6. Presentation

## Notes
- Keep your repository public
- Document setup instructions clearly
- Include a demo video
- Prepare a clear presentation
- Test thoroughly before submission

## Project Ideas & Implementation Insights
> Based on feedback from Horia Magureanu (Flare Research Scientist)

### Base Project: Documentation Chatbot
1. **Core Focus Areas**:
   - Data preparation and pre-processing
   - Improving retrieval pipeline beyond basic cosine similarity
   - Handling document size limitations (max 10kb for Gemini embeddings)

### Data Sources & Extensions
1. **Current Available Data**:
   - Flare developer hub content (provided in `src/data/*.csv`)

2. **Potential Additional Sources**:
   - Flare website content
   - Twitter feeds
   - Blog posts
   - Flare Foundation repositories
   - Oracle data feeds

### Cross-Track Integration
- Combine RAG with other tracks:
  - Example: RAG + DeFAI - Create a DeFi bot powered by Flare ecosystem data
  - Potential for multi-track submissions

### Key Success Factors
1. **Clear Use Case**:
   - Define specific target audience
   - Outline concrete problem being solved

2. **Verifiability Focus**:
   - Implement source referencing
   - Include links to original content
   - Provide verification mechanisms

3. **Technical Requirements**:
   - Must run inside a Trusted Execution Environment (TEE)
   - Follow TEE setup instructions in README

### Implementation Challenges
1. **Data Processing**:
   - Document size limitations (10kb for Gemini embeddings)
   - Content chunking strategies
   - Metadata preservation

2. **Retrieval Optimization**:
   - Beyond basic cosine similarity
   - Context-aware search
   - Relevance ranking

3. **Response Quality**:
   - Source attribution
   - Fact verification
   - Answer completeness

## TEE Deployment Details

### Environment Variables in TEE
```bash
# Core Variables
tee-env-GEMINI_API_KEY=$GEMINI_API_KEY
tee-env-TUNED_MODEL_NAME=$TUNED_MODEL_NAME
tee-env-SIMULATE_ATTESTATION=false

# Additional Variables (if needed)
tee-env-<ENV_VAR_NAME>=<ENV_VAR_VALUE>
```

### Machine Types & Zones
1. **AMD SEV**:
   - Zone: `us-central1-c`
   - Machine: `n2d-standard-2`
   - CPU Platform: "AMD Milan"
   - Image: `confidential-space-debug-250100`

2. **Intel TDX**:
   - Zone: `us-central1-a`
   - Machine: `c3-standard-4`
   - Image: `confidential-space-debug-0-tdxpreview-c38b622`

### Network Configuration
```bash
--network-interface=network-tier=PREMIUM,nic-type=GVNIC,stack-type=IPV4_ONLY,subnet=default
--tags=flare-ai,http-server,https-server
```

### Security Settings
1. **Shielded VM**:
   - Secure boot enabled
   - Virtual TPM enabled
   - Integrity monitoring enabled

2. **Service Account**:
   - Full cloud platform scope
   - Standard provisioning model

## Project Submission Requirements

### Repository Structure
1. **Documentation**:
   - README.md with setup instructions
   - Architecture diagram
   - API documentation
   - Environment variable list

2. **Code Organization**:
   - Clean folder structure
   - Commented code
   - Type hints
   - Error handling

3. **Testing**:
   - Unit tests
   - Integration tests
   - Performance benchmarks

### Deployment Package
1. **Container Image**:
   - Public accessibility
   - Version tagged
   - Size optimized

2. **Environment Files**:
   - `.env.example` template
   - Documentation of all variables
   - Secure defaults

### Demo Requirements
1. **Video Presentation**:
   - Architecture overview
   - Live demo
   - Key features
   - Technical innovations

2. **Documentation**:
   - Setup guide
   - Usage examples
   - API reference
   - Troubleshooting guide

## Technical Specifications

### Performance Requirements
1. **Response Time**:
   - Query processing < 5s
   - Vector search optimization
   - Batch processing capability

2. **Resource Usage**:
   - Memory efficient embeddings
   - Optimized vector storage
   - Efficient data chunking

### Security Implementation
1. **TEE Integration**:
   - Attestation verification
   - Secure key management
   - Data encryption

2. **API Security**:
   - Rate limiting
   - Input validation
   - Error handling
   - Logging

### Scalability Considerations
1. **Data Processing**:
   - Efficient chunking
   - Batch processing
   - Incremental updates

2. **Vector Database**:
   - Collection management
   - Index optimization
   - Query optimization

### Monitoring & Logging
1. **Application Logs**:
   ```bash
   # View specific instance logs
   gcloud logging read "resource.type=gce_instance AND resource.labels.instance_id=YOUR_INSTANCE_ID" --project=verifiable-ai-hackathon --format="table(timestamp,textPayload)"
   ```

2. **Performance Metrics**:
   - Query latency
   - Memory usage
   - API response times

3. **Error Tracking**:
   - Structured error logging
   - Error categorization
   - Resolution tracking

## Additional Resources

### Documentation Links
- [Flare Developer Hub](https://dev.flare.network/intro/)
- [Google Cloud Confidential Computing](https://cloud.google.com/confidential-computing)
- [Gemini API Documentation](https://ai.google.dev/docs)
- [Qdrant Documentation](https://qdrant.tech/documentation/)

### Support Channels
1. **Technical Support**:
   - Telegram: [https://t.me/+StI5VEIvtIg2ODlh](https://t.me/+StI5VEIvtIg2ODlh)
   - Email: [email protected]

2. **Documentation**:
   - Flare Developer Hub
   - Google Cloud docs
   - Template READMEs

3. **Office Hours**:
   - Google Cloud Support & Mentorship
   - Flare team availability
   - Technical workshops 