import os
import openai
from app.core.config import settings

class AIService:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if self.api_key:
            openai.api_key = self.api_key
    
    def generate_smart_answer(self, query: str, context: str, intent: str = "GENERAL_KNOWLEDGE") -> str:
        """
        REDESIGNED AI ANSWER GENERATION
        Dynamic prompt construction based on intent type.
        Fresh message arrays per request - no caching.
        """
        print(f"[AI SERVICE] generate_smart_answer called")
        print(f"[AI SERVICE] Intent: {intent}")
        print(f"[AI SERVICE] Query: {query[:100]}...")
        print(f"[AI SERVICE] Context length: {len(context)} chars")
        
        # STEP 1: Dynamic System Prompt Construction based on Intent
        if intent == "GENERAL_KNOWLEDGE":
            system_prompt = """You are an expert regulatory intelligence assistant specializing in pharmaceutical and medical device regulations.

Provide clear, accurate explanations of regulatory concepts, processes, and requirements using your general knowledge.

Guidelines:
- Answer conceptual and educational questions directly
- Use professional but accessible language
- Reference regulatory frameworks (FDA, EMA, ICH, WHO) when relevant
- Be comprehensive but concise
- Structure answers with bullet points when appropriate
- DO NOT fabricate specific updates or documents
- If asked about recent/current updates and you don't have specific documents, acknowledge this and provide general guidance

You are answering from general regulatory knowledge, NOT from document retrieval.
If the user asks about recent updates or specific authorities and you lack document context, be transparent about that limitation."""
        
        elif intent == "LIST_REQUEST":
            system_prompt = """You are a regulatory intelligence assistant.

The user wants a structured list. Provide:
- Clear bullet-point format
- One item per line
- Brief description for each item
- Organized by category if applicable

If documents are provided, extract and list the key items. If not, provide a general list from regulatory knowledge."""
        
        elif intent == "COMPARISON_REQUEST":
            system_prompt = """You are a regulatory intelligence assistant.

The user wants a comparison. Provide:
- Side-by-side comparison format
- Key differences and similarities
- Structured presentation (table or organized sections)
- Factual, balanced analysis

If documents are provided, use them. Otherwise, use general regulatory knowledge for standard comparisons."""
        
        elif intent == "SUMMARY_REQUEST":
            system_prompt = """You are a regulatory intelligence assistant.

The user wants a concise summary. Provide:
- Brief, focused summary
- Key points only (3-5 maximum)
- Clear and direct language
- No unnecessary details

If documents are provided, summarize them. Otherwise, provide a brief overview from general knowledge."""
        
        elif intent == "DATABASE_QUERY":
            system_prompt = """You are a regulatory intelligence assistant with access to a database of regulatory updates.

You will be provided with recent regulatory documents retrieved from the database.

Your role:
1. Analyze the provided documents carefully
2. Answer the user's question using ONLY information from these documents
3. Synthesize information from multiple documents when relevant
4. Cite specific details (dates, authorities, key points)
5. Be clear about what the documents cover and what they don't
6. Provide actionable insights when applicable
7. NEVER fabricate or infer details not explicitly in the documents

The documents are formatted as:
Authority: [Name]
Date: [Date]
Title: [Title]
Summary: [Summary]

If documents are provided, answer strictly based on them.
If no documents are provided, you cannot answer this query - explain that no matching updates were found."""
        
        else:
            # Default to general knowledge prompt
            system_prompt = """You are an expert regulatory intelligence assistant. Provide accurate, helpful information about pharmaceutical and medical device regulations."""
        
        # STEP 2: Use OpenAI API if available
        if self.api_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=self.api_key)
                
                # STEP 3: Build fresh message array (no caching)
                messages = [{"role": "system", "content": system_prompt}]
                
                # STEP 4: Add context if provided (for database queries)
                if context.strip():
                    user_message = f"""Context documents:

{context}

---

User question: {query}"""
                else:
                    user_message = query
                
                messages.append({"role": "user", "content": user_message})
                
                # STEP 5: Log actual prompt being sent
                print(f"[AI SERVICE] System prompt: {system_prompt[:100]}...")
                print(f"[AI SERVICE] User message length: {len(user_message)} chars")
                print(f"[AI SERVICE] Messages array: {len(messages)} messages")
                
                # STEP 6: Call GPT-4 Turbo with intent-based temperature
                temperature = 0.3 if intent == "DATABASE_QUERY" else 0.7
                max_tokens = 800 if intent == "COMPARISON_REQUEST" else 600
                
                print(f"[AI SERVICE] Calling GPT-4 Turbo (temp={temperature}, max_tokens={max_tokens})")
                
                response = client.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                
                answer = response.choices[0].message.content
                print(f"[AI SERVICE] GPT-4 response: {len(answer)} chars")
                print(f"[AI SERVICE] Finish reason: {response.choices[0].finish_reason}")
                return answer
                
            except Exception as e:
                print(f"[AI SERVICE] OpenAI error: {e}")
                print(f"[AI SERVICE] Falling back to mock response")
        
        # STEP 7: Mock responses when OpenAI unavailable (development fallback)
        return self._generate_mock_answer(query, context, intent)
    
    def generate_formatted_answer(self, query: str, context: str, intent: str, 
                                authority: str = None, sources: list = None, 
                                num_sources: int = 0) -> str:
        """
        Generate PRECISELY FORMATTED answers (100-200 words) with:
        - Clear headings
        - Bullet key points
        - Official source links
        - Authority-specific content (NO generic theory)
        """
        print(f"[FORMATTED ANSWER] Intent: {intent}, Authority: {authority}, Sources: {num_sources}")
        
        if not self.api_key:
            return self._generate_mock_formatted_answer(query, context, intent, authority, sources)
        
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            
            # Construct specific system prompt for formatted responses
            system_prompt = f"""You are a precise regulatory intelligence assistant.

Generate response for a {intent} query about {authority or 'regulatory topics'}.

REQUIREMENTS:
1. Length: 100-200 words MAXIMUM
2. Format: 
   - Main heading (bold)
   - 2-3 key bullet points
   - Specific facts ONLY (no generic regulatory theory)
   - Authority-specific content ONLY
3. Content:
   - Focus EXCLUSIVELY on the documents provided
   - Do NOT add general regulatory information
   - Do NOT explain common processes
   - Include specific dates, names, actions from documents
4. Source attribution:
   - End with official source link
   - Format: "**Source:** [Authority] - [URL]"

If documents provided are insufficient or off-topic:
"No relevant information found in documents for this query."

NEVER:
- Explain what FDA is or how approvals generally work
- Add information not in documents
- Exceed 200 words"""
            
            # Build user message with documents
            if sources and len(sources) > 0:
                source_info = "\n\nOfficial Sources:\n"
                for src in sources:
                    if src.get('url'):
                        source_info += f"- {src['title']}: {src['url']}\n"
                
                user_message = f"""Query: {query}

Authority: {authority or 'Multiple'}

Retrieved Documents:
{context}

{source_info}

Generate a precise, 100-200 word response with clear format as specified."""
            else:
                user_message = f"""Query: {query}
Authority: {authority or 'N/A'}

No documents retrieved for this query. 
Provide appropriate message."""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            
            # Call OpenAI with stricter parameters
            response = client.chat.completions.create(
                model="gpt-4-turbo",
                messages=messages,
                temperature=0.2,  # Lower temp for precise responses
                max_tokens=300,   # Strict word limit
            )
            
            answer = response.choices[0].message.content
            print(f"[FORMATTED ANSWER] Generated: {len(answer)} chars")
            return answer
            
        except Exception as e:
            print(f"[FORMATTED ANSWER] OpenAI error: {e}")
            return self._generate_mock_formatted_answer(query, context, intent, authority, sources)
    
    def _generate_mock_formatted_answer(self, query: str, context: str, intent: str,
                                       authority: str = None, sources: list = None) -> str:
        """Generate formatted mock response when OpenAI unavailable."""
        query_lower = query.lower()
        
        # If we have documents, format based on intent
        if context.strip():
            auth_prefix = f"{authority} " if authority else ""
            
            if "guideline" in query_lower:
                heading = f"**{authority or 'Regulatory'} Guidelines**"
                content = "Key requirements identified in documents:\n"
                content += "- Primary requirement from guidelines\n"
                content += "- Implementation timeline\n"
                content += "- Compliance mechanism\n"
            
            elif "regulation" in query_lower or "compliance" in query_lower:
                heading = f"**{authority or 'Regulatory'} Requirements**"
                content = "Regulatory obligations identified:\n"
                content += "- Main requirement\n"
                content += "- Affected entities\n"
                content += "- Deadline/timeline\n"
            
            elif "policy" in query_lower:
                heading = f"**{authority or 'Agency'} Policy**"
                content = "Policy details from documents:\n"
                content += "- Policy objective\n"
                content += "- Implementation scope\n"
                content += "- Key stakeholders\n"
            
            elif "list" in intent.lower():
                heading = f"**{authority or 'Relevant'} Items**"
                content = "Key items from documents:\n"
                content += "- Item 1 from documents\n"
                content += "- Item 2 from documents\n"
                content += "- Item 3 from documents\n"
            
            else:
                heading = f"**{authority or 'Update'}**"
                content = "Information from documents:\n"
                content += "- Key fact 1\n"
                content += "- Key fact 2\n"
                content += "- Key fact 3\n"
            
            # Add source link
            source_link = ""
            if sources and len(sources) > 0:
                first_source = sources[0]
                if first_source.get('url'):
                    source_link = f"\n\n**Source:** {first_source.get('authority', authority)} - {first_source['url']}"
            
            return f"{heading}\n\n{content}{source_link}"
        else:
            # No documents
            return f"No specific documents found in database for {authority or 'this'} query.\n\n" \
                   f"Please try:\n" \
                   f"- Refining your search terms\n" \
                   f"- Specifying which authority to search\n" \
                   f"- Checking official sources directly"
    
    def _generate_mock_answer(self, query: str, context: str, intent: str) -> str:
        """Generate high-quality mock responses when OpenAI is not available."""
        query_lower = query.lower()
        
        if intent == "GENERAL_KNOWLEDGE":
            # General knowledge responses based on common regulatory topics
            if "regulatory affairs" in query_lower:
                return """Regulatory affairs is a profession within regulated industries (pharmaceuticals, medical devices, biologics, etc.) that ensures products comply with all applicable laws and regulations.

**Key responsibilities:**
• Preparing and submitting regulatory applications (NDA, BLA, PMA, etc.)
• Maintaining ongoing compliance with regulatory requirements
• Managing communications with regulatory authorities (FDA, EMA, MHRA, etc.)
• Monitoring regulatory intelligence and industry changes
• Ensuring labeling and promotional materials meet regulatory standards

Regulatory affairs professionals bridge the gap between scientific development, legal requirements, and business strategy to bring safe and effective products to market."""
            
            elif "pharmacovigilance" in query_lower or "drug safety" in query_lower:
                return """Pharmacovigilance (PV) is the science and activities relating to the detection, assessment, understanding, and prevention of adverse effects or any other drug-related problems.

**Core activities:**
• Collecting and analyzing adverse event reports
• Signal detection and risk assessment
• Preparing Periodic Safety Update Reports (PSURs)
• Managing Risk Evaluation and Mitigation Strategies (REMS)
• Coordinating with regulatory authorities on safety issues

**Importance:**
- Ensures patient safety throughout a product's lifecycle
- Meets regulatory requirements globally (FDA, EMA, WHO)
- Protects public health through proactive risk management
- Maintains product licenses and market authorization"""
            
            elif "gmp" in query_lower or "good manufacturing" in query_lower:
                return """Good Manufacturing Practice (GMP) is a system ensuring products are consistently produced and controlled according to quality standards.

**Key GMP principles:**
• Well-designed and maintained facilities and equipment
• Qualified and trained personnel
• Validated manufacturing processes and procedures
• Complete and accurate documentation
• Comprehensive quality control testing
• Robust quality management systems

**Regulatory frameworks:**
- FDA: 21 CFR Parts 210, 211 (drugs)
- EMA: Eudralex Volume 4
- WHO: Technical Report Series
- ICH Q7: GMP Guide for Active Pharmaceutical Ingredients

Non-compliance can result in warning letters, import alerts, or recalls."""
            
            elif "clinical trial" in query_lower:
                return """Clinical trials are research studies performed on human participants to evaluate the safety and efficacy of medical interventions.

**Phase structure:**
• **Phase I:** Safety and dosage (20-80 people)
• **Phase II:** Efficacy and side effects (100-300 people)
• **Phase III:** Confirmation in large populations (1,000-3,000+ people)
• **Phase IV:** Post-marketing surveillance

**Regulatory requirements:**
- IND (Investigational New Drug) application with FDA
- IRB (Institutional Review Board) approval
- GCP (Good Clinical Practice) compliance
- Informed consent from all participants
- Ongoing data reporting to regulatory authorities"""
            
            else:
                return f"""Based on regulatory knowledge regarding: **"{query}"**

In the pharmaceutical and medical device regulatory context, this relates to compliance frameworks that ensure products meet safety, efficacy, and quality standards.

**Key considerations:**
• Requirements vary by geographic region (FDA, EMA, MHRA, etc.)
• Product type determines applicable regulations
• Risk classification affects oversight level
• Manufacturing and quality systems must be validated

**Resources:**
1. Official regulatory authority websites
2. ICH (International Council for Harmonisation) guidelines
3. Recent regulatory updates and guidance documents
4. Regulatory affairs specialists

Would you like information about a specific regulatory authority or topic?"""
        
        elif intent == "DATABASE_QUERY":
            # Database query with context
            if context.strip():
                # Extract key info from context
                lines = context.split('\n')
                titles = []
                authorities = []
                for line in lines:
                    if line.startswith('Title:'):
                        titles.append(line.replace('Title:', '').strip())
                    elif line.startswith('Authority:'):
                        authorities.append(line.replace('Authority:', '').strip())
                
                unique_authorities = list(set(authorities))
                authority_str = ', '.join(unique_authorities) if unique_authorities else 'regulatory authorities'
                
                answer = f"""Based on the retrieved regulatory updates from {authority_str}:

**Relevant Updates:**\n"""
                for i, title in enumerate(titles[:5], 1):
                    answer += f"{i}. {title}\n"
                
                answer += f"""\n**Key insights:**
• These updates address recent regulatory developments relevant to your query
• Organizations should review these documents for applicability to their operations
• Compliance with new requirements should be prioritized
• Consider consulting with regulatory specialists for implementation guidance

Refer to the source documents for detailed requirements and timelines."""
                return answer
            else:
                return f"""I searched for regulatory updates matching your query about "{query}" but could not find documents with sufficient relevance to confidently answer your question.

**Why no results:**
- The database does not currently contain updates matching your specific criteria
- Documents available don't meet the relevance threshold for your query
- The search terms may not match available regulatory updates

**Recommendations:**
- Try rephrasing your query with different keywords
- Specify a regulatory authority if searching for updates from a particular source (FDA, EMA, ICH, MHRA, PMDA, CDSCO, NMPA)
- Check official authority websites for the latest regulatory updates
- Ask about general regulatory processes instead (e.g., "What is the drug approval process?" rather than "Any FDA updates on drug X?")"""
        
        elif intent == "LIST_REQUEST":
            if context.strip():
                # Extract and list items from context
                lines = context.split('\n')
                titles = [line.replace('Title:', '').strip() for line in lines if line.startswith('Title:')]
                
                answer = "**Regulatory Updates:**\n\n"
                for i, title in enumerate(titles, 1):
                    answer += f"{i}. {title}\n"
                return answer
            else:
                return f"""**{query}:**

1. Item 1 - Description
2. Item 2 - Description
3. Item 3 - Description

*Note: For current regulatory updates, please query with specific authority names or timeframes.*"""
        
        elif intent == "COMPARISON_REQUEST":
            return f"""**Comparison: {query}**

**Aspect 1:**
- Option A: Details
- Option B: Details

**Aspect 2:**
- Option A: Details
- Option B: Details

**Key Differences:**
- Difference 1
- Difference 2

**Similarities:**
- Similarity 1
- Similarity 2"""
        
        elif intent == "SUMMARY_REQUEST":
            if context.strip():
                return f"""**Summary:**

Key points from the retrieved regulatory documents:
- Main point 1
- Main point 2
- Main point 3

Refer to source documents for full details."""
            else:
                return f"""**Brief Overview: {query}**

Key concepts:
- Point 1
- Point 2
- Point 3

For detailed information, consult official regulatory guidance."""
        
        else:
            return f"""Regarding your query: "{query}"

Please consult official regulatory authority resources for the most accurate and current information."""

    def analyze_update(self, update_title: str, update_summary: str, full_text: str, difficulty_level: str = "professional") -> dict:
        """Generates compliance-focused analysis of a regulatory update."""
        print(f"[AI SERVICE] Analyzing update: {update_title[:80]}")
        print(f"[AI SERVICE] Difficulty level: {difficulty_level}")
        
        # Context-aware analysis based on update content
        title_lower = update_title.lower()
        summary_lower = (update_summary or "").lower()
        full_lower = (full_text or "").lower()
        combined = f"{title_lower} {summary_lower} {full_lower}"
        
        # Enhanced type detection
        is_approval = any(word in combined for word in ["approv", "approved", "authorization", "authorized", "granted"])
        is_safety = any(word in combined for word in ["safety", "adverse", "warning", "precaution", "risk", "contraindication"])
        is_recall = "recall" in combined or "withdrawn" in combined or "suspension" in combined
        is_urgent = "recall" in combined or "urgent" in combined or "immediate" in combined or "warning" in combined
        is_guidance = any(word in combined for word in ["guidance", "guideline", "requirement", "regulation", "policy"])
        is_clinical = any(word in combined for word in ["clinical", "trial", "study", "data", "efficacy"])
        is_manufacturing = any(word in combined for word in ["manufacturing", "production", "facility", "quality", "cGMP"])
        
        # Determine risk level
        if is_recall or (is_safety and is_urgent):
            risk = "High"
        elif is_safety or is_manufacturing:
            risk = "Medium"
        else:
            risk = "Low"
        
        # Extract key details for specific bullet points
        # Extract product/topic from title - look for keywords before colons or dashes
        title_parts = [p.strip() for p in update_title.replace(':', '-').split('-')]
        main_topic = title_parts[0] if title_parts else update_title
        specific_issue = None
        
        # Try to extract more specific info
        if "medical device" in title_lower:
            specific_issue = "medical devices"
        elif "drug" in title_lower:
            specific_issue = "pharmaceutical products"
        elif "vaccine" in title_lower:
            specific_issue = "vaccines"
        elif "biologic" in title_lower or "biologics" in title_lower:
            specific_issue = "biologic products"
        elif "facility" in title_lower or "manufacturing" in title_lower:
            specific_issue = "manufacturing facilities"
        
        # Generate context-specific analysis
        if difficulty_level == "professional":
            if is_safety or is_recall:
                # Safety/recall specific - Extract specific product if mentioned
                if "approved" in title_lower or "new drug" in title_lower:
                    drug_name = update_title.split('(')[1].split(')')[0] if '(' in update_title else "the approved product"
                else:
                    drug_name = specific_issue or main_topic
                
                return {
                    "summary": f"Critical safety alert: {update_title}. Immediate action required. Organization must identify all product inventory related to {drug_name}, quarantine affected units, and assess patient exposure. Root cause investigation must determine whether issue is product-specific, manufacturer-specific, or batch-specific. Enhanced vigilance is required across distribution channels. Regulatory reporting to relevant authorities is mandatory within specified timeframes.",
                    "action_items": [
                        f"Audit entire inventory of {drug_name} - identify quantities, batch numbers, and current distribution status",
                        f"Issue immediate halt to distribution of {drug_name} pending safety assessment completion",
                        f"Implement traceability protocol to locate all patients/healthcare facilities that received {drug_name}",
                        f"Evaluate root cause: Is this product-specific, manufacturing-related, or batch-specific contamination?",
                        f"File urgent safety report with regulatory authority and prepare healthcare provider communication"
                    ],
                    "risk_level": risk
                }
            elif is_approval or is_clinical:
                # Approval/clinical specific
                # Extract the specific drug/product name if available
                if '(' in update_title and ')' in update_title:
                    product_name = update_title.split('(')[1].split(')')[0]
                elif 'list of' in title_lower:
                    product_name = "newly approved drugs"
                else:
                    product_name = specific_issue or "the approved product"
                
                return {
                    "summary": f"Regulatory approval announced: {update_title}. {product_name.title()} has received authorization for manufacture, distribution, and marketing. This milestone creates immediate commercialization opportunity and establishes market entry timeline. Organizations holding approvals must establish supply chain and distribution infrastructure rapidly. Pharmacovigilance obligations begin upon approval - baseline and enhanced monitoring depending on approval conditions. First-to-market advantage available for rapid launch execution.",
                    "action_items": [
                        f"Verify procurement capability for raw materials and manufacturing inputs needed for {product_name.lower()}",
                        f"Establish distribution network and regulatory-compliant supply chain for {product_name.lower()}",
                        f"Design and implement pharmacovigilance protocol specific to {product_name.lower()}'s safety profile and approval conditions",
                        f"Develop pricing strategy and market positioning for {product_name.lower()} competitive assessment",
                        f"Create launch timeline with regulatory, commercial, and operational milestones for {product_name.lower()}"
                    ],
                    "risk_level": "Low"
                }
            elif is_manufacturing:
                # Manufacturing/quality specific
                manufacturing_topic = specific_issue or "manufacturing and quality systems"
                return {
                    "summary": f"Regulatory requirement issued: {update_title}. New standards for {manufacturing_topic} have been established and are enforceable. All manufacturing sites, contract manufacturers, and quality partners must conduct comprehensive gap analysis immediately. Compliance demonstration requires documented validation, qualifications, and audits. Deadline for compliance varies by authority and facility size - prioritize high-risk manufacturing processes.",
                    "action_items": [
                        f"Conduct comprehensive audit of current {manufacturing_topic.lower()} against new regulatory requirements",
                        f"Identify all production lines, equipment, and processes that require validation updates for {manufacturing_topic.lower()}",
                        f"Develop validation protocol and execute equipment qualification (IQ, OQ, PQ) for impacted {manufacturing_topic.lower()} systems",
                        f"Review and revise standard operating procedures (SOPs) for all aspects of {manufacturing_topic.lower()} to demonstrate compliance",
                        f"Schedule inspector notification/pre-approval inspection (PAI) to verify {manufacturing_topic.lower()} compliance before regulatory review"
                    ],
                    "risk_level": "Medium"
                }
            elif is_guidance:
                # General guidance specific - Extract topic more effectively
                if ':' in update_title:
                    guidance_topic = update_title.split(':')[1].strip()
                else:
                    guidance_topic = main_topic
                
                return {
                    "summary": f"Regulatory guidance issued: {update_title}. This guidance on {guidance_topic.lower()} establishes mandatory compliance expectations for all regulated entities. The authority has signaled enforcement focus on this area - non-compliance will trigger warning letters and enforcement actions. Organizations must prioritize review and implementation. Documented evidence of good-faith compliance efforts is essential for enforcement defense.",
                    "action_items": [
                        f"Obtain, read, and analyze the official guidance document on {guidance_topic.lower()} in detail - identify all sub-sections",
                        f"Conduct risk assessment: Where does your organization currently fall short of {guidance_topic.lower()} expectations?",
                        f"Map internal processes against {guidance_topic.lower()} requirements and identify specific gaps requiring remediation",
                        f"Assign ownership for each remediation item and establish completion deadlines with regulatory timeline expectations",
                        f"Train all affected personnel on {guidance_topic.lower()} requirements and implement monitoring to sustain compliance"
                    ],
                    "risk_level": "Medium"
                }
            else:
                # Generic regulatory update - still specific to the title
                regulatory_focus = specific_issue or main_topic.lower()
                return {
                    "summary": f"Regulatory update: {update_title}. This notification addresses compliance expectations for {regulatory_focus}. Organizations should assess industry impact and determine whether requirements apply to their operations. Regulatory authority is actively monitoring compliance in this area. Organizations should implement or update procedures and documentation to demonstrate ongoing awareness and commitment.",
                    "action_items": [
                        f"Review the regulatory update carefully and understand specific requirements related to {regulatory_focus}",
                        f"Assess whether your organization manufactures, distributes, or is otherwise responsible for {regulatory_focus}",
                        f"Evaluate current processes and procedures against {regulatory_focus} requirements identified in the update",
                        f"Document findings from your assessment of {regulatory_focus} compliance posture and any identified gaps",
                        f"Communicate {regulatory_focus} compliance status to executive leadership and establish accountability"
                    ],
                    "risk_level": risk
                }
        
        elif difficulty_level == "legal":
            if is_recall or (is_safety and is_urgent):
                # Extract product for legal analysis
                if '(' in update_title and ')' in update_title:
                    product_name = update_title.split('(')[1].split(')')[0]
                else:
                    product_name = specific_issue or "affected products"
                
                return {
                    "summary": f"CRITICAL: {update_title} creates severe legal exposure. The regulatory safety action triggers mandatory adverse event reporting obligations with criminal liability for false or delayed reporting. Product liability exposure is immediate - expect class action lawsuits from affected patients. The organization may face civil settlements, consent decrees, or criminal prosecution. Insurance coverage must be activated immediately. All documents and communications are subject to legal hold - privilege protections are mandatory.",
                    "action_items": [
                        f"URGENT: Retain external product liability counsel to assess litigation risk exposure for {product_name}",
                        f"Issue legal hold notice for ALL documents related to {{product_name}} - manufacturing, testing, complaints, and communications",
                        f"File mandatory adverse event reports to regulatory authorities regarding {{product_name}} within required timeframes",
                        f"Notify all product liability and recall insurance carriers immediately with preliminary claim information for {{product_name}}",
                        f"Establish privileged communication protocols - all analysis and response to {{product_name}} issue must be directed through legal counsel"
                    ],
                    "risk_level": "High"
                }
            else:
                # Non-emergency legal analysis
                legal_topic = specific_issue or main_topic.lower()
                return {
                    "summary": f"Legal impact assessment: {update_title}. This regulatory update creates documented compliance obligations for {legal_topic}. Non-compliance triggers enforcement action - warning letters, consent decrees, and civil penalties up to $[amount] per violation per day. Written policies demonstrating good-faith compliance efforts provide enforcement defense. Board-level awareness of {{legal_topic}} compliance status should be documented.",
                    "action_items": [
                        f"Retain legal counsel to assess enforcement risk and compliance obligations specific to {{legal_topic}}",
                        f"Audit current written policies and procedures to verify adequate coverage of {{legal_topic}} requirements",
                        f"Document risk assessment findings regarding {{legal_topic}} - identify any areas where organization cannot currently demonstrate compliance",
                        f"Establish executive accountability and reporting on {{legal_topic}} compliance status - board minutes should reflect management attestation",
                        f"Implement ongoing legal compliance monitoring for {{legal_topic}} with documented corrective action tracking"
                    ],
                    "risk_level": risk
                }
        
        else:  # beginner
            if is_recall or is_safety:
                # Extract specific product info
                if '(' in update_title and ')' in update_title:
                    product_mentioned = update_title.split('(')[1].split(')')[0]
                else:
                    product_mentioned = specific_issue or "the affected product"
                
                return {
                    "summary": f"Safety Notice: {update_title}. A serious safety problem has been found with {product_mentioned}. The regulatory agency is requiring action to protect patients. If your company makes or sells {product_mentioned}, you need to act right away. Patients using {product_mentioned} may be at risk and may need to be contacted.",
                    "action_items": [
                        f"Determine if your company manufactures, imports, distributes, or sells {product_mentioned}",
                        f"If yes, find all {product_mentioned} in your inventory and storage facilities - list quantities and batch numbers",
                        f"Stop selling or shipping {product_mentioned} until you understand the safety issue",
                        f"Check if anyone you sold {product_mentioned} to has received complaints or adverse event reports",
                        f"Report what you find to the regulatory authority within 15 days"
                    ],
                    "risk_level": risk
                }
            elif is_approval:
                # Extract specific product for beginner
                if '(' in update_title and ')' in update_title:
                    product_info = update_title.split('(')[1].split(')')[0]
                elif 'list of' in title_lower or 'posted' in title_lower:
                    product_info = "the newly approved products/drugs"
                else:
                    product_info = specific_issue or "the approved product"
                
                return {
                    "summary": f"Good News: {update_title}. The regulatory agency has approved {product_info}. Permission has been granted to make and sell {product_info}. Doctors and patients can now use {product_info}. The company must make sure it is safe and works as promised.",
                    "action_items": [
                        f"Make sure you understand what {product_info} is approved for (what disease/condition it treats)",
                        f"Check if your company makes or plans to sell {product_info}",
                        f"If yes, plan how to make {product_info} and get it to pharmacies and hospitals",
                        f"Set up a system to watch for any problems or complaints about {product_info} after it is sold",
                        f"Train your sales and customer service teams on facts about {product_info}"
                    ],
                    "risk_level": "Low"
                }
            else:
                # Beginner generic/guidance
                beginner_topic = specific_issue or main_topic.lower()
                return {
                    "summary": f"New Rules: {update_title}. The regulatory agency has announced new rules about {beginner_topic}. Companies need to follow these new rules. If your company works with {beginner_topic}, you need to understand and follow these rules. Failing to follow the rules can result in fines or other government action.",
                    "action_items": [
                        f"Read the official update or guidance about {beginner_topic} - understand the main points",
                        f"Determine if {beginner_topic} rules apply to your company",
                        f"Ask your manager/legal team if your company is already following {beginner_topic} rules",
                        f"If changes are needed, work with your team to implement {beginner_topic} rule compliance",
                        f"Make sure all employees understand {beginner_topic} rules through training or briefings"
                    ],
                    "risk_level": risk
                }
    
    
    def _extract_authority(self, query_lower: str) -> str:
        """Extract the regulatory authority from query."""
        if "fda" in query_lower or "united states" in query_lower or "us" in query_lower:
            return "FDA (United States)"
        elif "ema" in query_lower or "european" in query_lower or "europe" in query_lower:
            return "EMA (European Medicines Agency)"
        elif "ich" in query_lower or "harmonisation" in query_lower or "harmonization" in query_lower:
            return "ICH (International Council for Harmonisation)"
        elif "mhra" in query_lower or "uk" in query_lower or "britain" in query_lower:
            return "MHRA (United Kingdom)"
        elif "pmda" in query_lower or "japan" in query_lower:
            return "PMDA (Japan)"
        elif "cdsco" in query_lower or "india" in query_lower:
            return "CDSCO (India)"
        elif "nmpa" in query_lower or "china" in query_lower:
            return "NMPA (China)"
        else:
            return "regulatory authorities"
    
    def _extract_topic(self, query_lower: str) -> str:
        """Extract the main topic from query."""
        if "artificial intelligence" in query_lower or ("ai" in query_lower and ("guideline" in query_lower or "guidance" in query_lower)):
            return "artificial intelligence (AI) in healthcare"
        elif "biosimilar" in query_lower:
            return "biosimilar development and approval"
        elif "medical device" in query_lower or "device" in query_lower:
            return "medical device regulations"
        elif "pharmacovigilance" in query_lower or "drug safety" in query_lower:
            return "pharmacovigilance and drug safety"
        elif "gmp" in query_lower or "manufacturing" in query_lower:
            return "Good Manufacturing Practice (GMP)"
        elif "clinical trial" in query_lower:
            return "clinical trial regulations"
        elif "labeling" in query_lower:
            return "product labeling requirements"
        else:
            return "regulatory compliance"

    def summarize(self, text: str, mode: str = "beginner") -> dict:
        """
        Generates a summary based on the selected mode.
        Modes: 'beginner', 'professional', 'legal'
        """
        if not self.api_key:
            return {
                "summary": f"[Mock] {mode.title()} summary: This regulatory update covers important changes. Review and assess impact.",
                "risk_level": "Medium",
                "action_items": ["Review compliance status", "Assess organizational impact", "Update protocols"],
                "stakeholders_affected": ["Quality", "Regulatory", "Legal"],
            }

        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            mode_prompt = {
                "beginner": "Explain in simple, non-technical terms for management.",
                "professional": "Detailed regulatory analysis with compliance implications.",
                "legal": "Legal binding, liability, and compliance analysis.",
            }
            response = client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {"role": "system", "content": "You are a pharmaceutical regulatory expert."},
                    {
                        "role": "user",
                        "content": f"{mode_prompt.get(mode, 'Summarize')}\n\nText: {text[:3000]}",
                    },
                ],
                temperature=0.5,
                max_tokens=800,
            )
            summary = response.choices[0].message.content
            return {
                "summary": summary,
                "risk_level": "High" if "critical" in summary.lower() else "Medium",
                "action_items": ["Review", "Validate", "Implement"],
                "stakeholders_affected": ["Quality", "Regulatory", "Legal"],
            }
        except Exception as e:
            print(f"OpenAI error: {e}")
            return {
                "summary": f"Error: {str(e)}",
                "risk_level": "Unknown",
                "action_items": ["Contact support"],
                "stakeholders_affected": [],
            }

ai_service = AIService()
