"""
AI Service using Groq API with Llama 3 Model
Handles RAG responses and general LLM queries with improved logging
"""
import os
import re
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv
from typing import Optional, Dict, Any

# Load .env from backend first, then from repo root if present
_SERVICE_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _SERVICE_DIR.parent.parent
_ROOT_DIR = _BACKEND_DIR.parent
load_dotenv(_BACKEND_DIR / ".env")
load_dotenv(_ROOT_DIR / ".env")


class AIService:
    """
    AI Service powered by Groq API with Llama 3-70b model
    Supports RAG mode (with database context) and general knowledge mode
    """
    
    def __init__(self):
        """Initialize Groq client"""
        self.api_key = os.getenv("GROQ_API_KEY")
        print(f"[AI SERVICE] GROQ_API_KEY present: {bool(self.api_key)}")
        print(f"[AI SERVICE] API Key prefix: {self.api_key[:20] if self.api_key else 'None'}...")
        
        if not self.api_key:
            print("[AI SERVICE] ERROR: GROQ_API_KEY not found in environment")
            self.client = None
        else:
            try:
                self.client = Groq(api_key=self.api_key)
                print("[AI SERVICE] Groq client initialized successfully")
            except Exception as e:
                print(f"[AI SERVICE] ERROR initializing Groq: {e}")
                import traceback
                traceback.print_exc()
                self.client = None
        
        # System prompt template (formatted per request with query + context)
        self.system_prompt_template = """You are a pharmaceutical regulatory expert.

User Query: {query}
Context: {context}
Query Mode: {query_mode}
Detected Authority: {authority}

Instructions:
- Identify regulatory authority mentioned (FDA, EMA, ICH, etc.)
- Focus ONLY on that authority unless comparison is explicitly asked
- If query includes "latest" or "recent":
    - Prioritize recent regulatory updates, guidelines, or policy changes
    - Mention years or document names if possible
- DO NOT give generic textbook explanations
- If context is available:
    - Use it FIRST
    - Extract specific facts
- If context is missing:
    - Use domain knowledge BUT stay specific to authority and cite concrete guidelines

Mandatory rule:
- Always give specific guidelines, frameworks, and real-world regulatory details. Avoid generic consulting language.

Response Format (always):
Title: <one-line answer title>
Specific Guidelines:
- <point 1>
- <point 2>
- <point 3>
Key Requirements:
- <requirement 1>
- <requirement 2>
Practical Implementation:
- <action 1>
- <action 2>
Latest Updates:
1. <latest item or trend>
2. <latest item or trend>
Sources:
- <source name or URL if available>

Formatting Rules:
- No markdown symbols such as **, ###, or fenced blocks
- Keep sections readable with blank lines
- If latest updates are unavailable, provide best current guidance in Latest Updates section
- Never output phrases like: AI unavailable, No data found, Use latest guidance, Consult authorities""" 

    def _response_style_hint(self, query: str, intent: str, query_mode: str) -> str:
        q = (query or "").lower()
        if query_mode == "latest":
            return "Answer as a fresh regulatory briefing. Lead with the newest concrete change, then explain impact and any affected authority or document."
        if "difference" in q or "compare" in q or "vs" in q:
            return "Answer as a direct comparison. Use contrasts, then short practical implications."
        if any(term in q for term in ["what is", "define", "meaning of", "explain"]):
            return "Answer as a precise explanation. Start with a one-sentence definition, then give 2-4 specific regulatory points."
        if any(term in q for term in ["how", "steps", "process", "implement"]):
            return "Answer as an implementation guide. Use step-by-step actions and avoid abstract theory."
        if intent == "LIST_REQUEST":
            return "Answer as a concise, well-grouped list with concrete items and no filler."
        return "Answer directly, avoid repetitive phrasing, and tailor the opening sentence to the specific query."

    def generate_smart_answer(
        self,
        query: str,
        context: str = "",
        intent: str = "GENERAL_KNOWLEDGE",
        detected_authority: Optional[str] = None,
        query_mode: str = "standard",
        retrieval_metrics: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate AI response using Groq Llama 3 model
        
        Args:
            query: User's question
            context: Retrieved documents (if RAG mode)
            intent: Query intent type
            detected_authority: Authority detected in query (FDA, EMA, etc.)
            retrieval_metrics: Metrics from RAG retrieval
            
        Returns:
            Generated answer string
        """
        print(f"\n[AI SERVICE] === generate_smart_answer called ===")
        print(f"[AI SERVICE] Query: {query[:80]}...")
        print(f"[AI SERVICE] Intent: {intent}")
        print(f"[AI SERVICE] Detected Authority: {detected_authority}")
        print(f"[AI SERVICE] Query Mode: {query_mode}")
        print(f"[AI SERVICE] Context length: {len(context)} chars")
        print(f"[AI SERVICE] Client available: {self.client is not None}")
        
        # Log retrieval metrics
        if retrieval_metrics:
            print(f"[AI SERVICE] Retrieval metrics: {retrieval_metrics}")
        
        # Check if we have valid Groq client
        if not self.client:
            print("[AI SERVICE] No Groq client available - using fallback")
            return self._generate_fallback_answer(query, context, intent, detected_authority, query_mode)
        
        try:
            # Build request-specific system prompt with injected query/context
            context_for_prompt = context.strip() if context and context.strip() else "No additional context provided."
            system_prompt = self.system_prompt_template.format(
                query=query.strip(),
                context=context_for_prompt,
                query_mode=query_mode,
                authority=detected_authority or "Not specified"
            )
            style_hint = self._response_style_hint(query, intent, query_mode)
            system_prompt = f"{system_prompt}\n\nStyle Hint:\n{style_hint}\n- Do not reuse the same opening sentence across different answers.\n- Prefer concrete nouns from the user query over generic phrasing."

            # Determine mode: RAG or General Knowledge
            if context.strip() and retrieval_metrics and retrieval_metrics.get("documents_injected", 0) > 0:
                mode = "RAG"
                print(f"[AI SERVICE] MODE: RAG (injecting {retrieval_metrics['documents_injected']} documents)")
                user_message = self._build_rag_prompt(query, context, detected_authority, query_mode, retrieval_metrics)
            else:
                mode = "GENERAL_KNOWLEDGE"
                print(f"[AI SERVICE] MODE: GENERAL_KNOWLEDGE (no document injection)")
                user_message = self._build_general_prompt(query, detected_authority, query_mode)
            
            # Log prompt details
            print(f"[AI SERVICE] User message length: {len(user_message)} chars")
            print(f"[AI SERVICE] Calling Groq API (model: llama-3.3-70b-versatile)...")
            
            # Call Groq API
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.3 if mode == "RAG" else 0.7,
                max_tokens=800,
                top_p=1,
                stream=False
            )
            
            answer = chat_completion.choices[0].message.content
            print(f"[AI SERVICE] Response received: {len(answer)} chars")
            print(f"[AI SERVICE] Finish reason: {chat_completion.choices[0].finish_reason}")
            print(f"[AI SERVICE] Tokens used: {chat_completion.usage.total_tokens if chat_completion.usage else 'N/A'}")
            
            normalized = self._normalize_response(answer)

            if self._is_response_generic(normalized, query=query, intent=intent, authority=detected_authority):
                print("[AI SERVICE] Response rejected as generic, rebuilding with strict factual prompt")
                strict_prompt = self._build_strict_factual_prompt(query, context_for_prompt, detected_authority)
                strict_completion = self.client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": strict_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    model="llama-3.3-70b-versatile",
                    temperature=0.2,
                    max_tokens=900,
                    top_p=1,
                    stream=False
                )
                normalized = self._normalize_response(strict_completion.choices[0].message.content)

            if self._is_response_generic(normalized, query=query, intent=intent, authority=detected_authority):
                print("[AI SERVICE] Strict retry still generic, using deterministic domain-grounded fallback")
                return self._generate_fallback_answer(query, context, intent, detected_authority, query_mode)

            return normalized
            
        except Exception as e:
            print(f"[AI SERVICE] Groq API error: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            print(f"[AI SERVICE] Falling back to static response")
            return self._generate_fallback_answer(query, context, intent, detected_authority, query_mode)

    def _normalize_response(self, answer: str) -> str:
        """Normalize model output to clean UI-friendly structured format."""
        cleaned = (answer or "").replace("**", "").replace("###", "").replace("##", "").strip()

        # If required sections already exist, return cleaned content.
        required = ["Title:", "Specific Guidelines:", "Key Requirements:", "Practical Implementation:", "Latest Updates:", "Sources:"]
        if all(section in cleaned for section in required):
            return cleaned

        lines = [ln.strip() for ln in cleaned.splitlines() if ln.strip()]
        title = lines[0] if lines else "Regulatory Guidance Summary"

        guidelines = []
        for ln in lines[1:]:
            if len(guidelines) >= 5:
                break
            if ln and not ln.lower().startswith(("title:", "key points:", "latest updates:", "actionable insights:", "sources:")):
                guidelines.append(ln.lstrip("- "))

        if not guidelines:
            guidelines = ["Topic-specific regulatory references based on query and authority context"]

        requirements = [
            "Map each guideline to dossier evidence expectations and validation strategy.",
            "Ensure submission modules include quality, safety, and efficacy evidence in required format.",
        ]
        implementation = [
            "Build a compliance matrix linking each guideline identifier to SOPs and submission sections.",
            "Run readiness checks before submission to close evidence and formatting gaps.",
        ]
        latest_updates = ["Use the latest authority updates by publication date and effective scope."]
        sources = ["Regulatory context and retrieved authority data"]

        return self._build_structured_response(title, guidelines, requirements, implementation, latest_updates, sources)

    def _build_strict_factual_prompt(self, query: str, context: str, authority: Optional[str]) -> str:
        authority_name = authority or "the requested authority"
        guidelines_hint = self._domain_guideline_pack(query, authority).get("guidelines", [])
        hint_text = ", ".join(guidelines_hint[:8]) if guidelines_hint else "Include concrete identifiers such as ICH M4, ICH Q1A(R2), ICH Q2(R2), 21 CFR references, 351(k) as applicable"
        if "ctd" in (query or "").lower() or "common technical document" in (query or "").lower():
            hint_text = "Include ICH M4 (CTD), Modules 1-5, and related ICH quality references such as Q1A(R2), Q2(R2), Q8(R2), Q9, Q10"
        focus_terms = self._focus_terms(query)
        focus_hint = ", ".join(focus_terms[:8]) if focus_terms else query
        return f"""You are a pharmaceutical regulatory expert.

Query: {query}
Authority: {authority_name}
Context: {context}
Focus terms that must be addressed directly: {focus_hint}

Return only factual, specific regulatory content with concrete identifiers.
Must include: {hint_text}

Output sections exactly:
Title:
Specific Guidelines:
Key Requirements:
Practical Implementation:
Latest Updates:
Sources:

Never use generic consulting phrases or vague advice."""

    def _requires_guideline_ids(self, query: str, intent: Optional[str]) -> bool:
        q = (query or "").lower()
        if intent in {"GUIDELINE_REQUEST", "REGULATION_REQUEST", "DOCUMENT_REQUEST", "DATABASE_QUERY"}:
            return True
        keywords = [
            "guideline", "guidance", "ctd", "module", "ich", "cfr", "regulation",
            "compliance", "biosimilar", "stability", "gmp", "gcp", "clinical",
        ]
        return any(k in q for k in keywords)

    def _focus_terms(self, query: str) -> list[str]:
        q = (query or "").lower()
        terms = re.findall(r"[a-zA-Z]{3,}", q)
        stop = {
            "what", "which", "when", "where", "why", "how", "about", "latest", "recent",
            "update", "updates", "tell", "explain", "show", "give", "please", "need",
            "does", "into", "from", "with", "that", "this", "there", "their", "your",
        }
        return [t for t in terms if t not in stop][:12]

    def _is_response_generic(self, answer: str, query: str = "", intent: Optional[str] = None, authority: Optional[str] = None) -> bool:
        text = (answer or "").lower()
        banned = ["ai unavailable", "no data found", "use latest guidance", "consult authorities", "consult official", "align to"]
        if any(b in text for b in banned):
            return True

        # Ensure response is topically aligned to query terms.
        focus = self._focus_terms(query)
        if focus:
            overlap = sum(1 for t in focus if t in text)
            if overlap == 0:
                return True

        # Only enforce explicit guideline-id presence when the query intent requires it.
        if self._requires_guideline_ids(query, intent):
            guideline_id_pattern = r"\b((ich\s*[qems]\d+[a-z]?(?:\(r\d+\))?)|(m\d)|(q\d+[a-z]?(?:\(r\d+\))?)|(21\s*cfr\s*(part\s*)?\d+)|(351\(k\))|(eu\s*\d{3,4}/\d{2,4}))\b"
            if not re.search(guideline_id_pattern, text, flags=re.IGNORECASE):
                return True

        if authority and authority.lower() not in text and self._requires_guideline_ids(query, intent):
            # For authority-specific regulatory asks, response should mention authority explicitly.
            return True

        required_sections = ["title:", "specific guidelines:", "key requirements:", "practical implementation:", "latest updates:", "sources:"]
        return not all(section in text for section in required_sections)

    def _domain_guideline_pack(self, query: str, authority: Optional[str]) -> Dict[str, Any]:
        q = (query or "").lower()
        auth = (authority or "").upper()

        if "ctd" in q or "common technical document" in q or (("module" in q) and ("ich" in q or auth == "ICH")):
            return {
                "title": "ICH CTD guidance framework",
                "guidelines": [
                    "ICH M4 Common Technical Document (CTD)",
                    "Module 1 Regional Administrative Information",
                    "Module 2 CTD Summaries",
                    "Module 3 Quality",
                    "Module 4 Nonclinical Study Reports",
                    "Module 5 Clinical Study Reports",
                    "ICH Q1A(R2) Stability Testing",
                    "ICH Q2(R2) Analytical Validation",
                    "ICH Q8(R2) Pharmaceutical Development",
                    "ICH Q9 Quality Risk Management",
                    "ICH Q10 Pharmaceutical Quality System",
                ],
                "requirements": [
                    "Organize dossier content strictly by CTD module structure.",
                    "Provide validated analytical methods and stability packages aligned to Q1A/Q2.",
                    "Demonstrate development rationale and control strategy aligned to Q8/Q9/Q10.",
                ],
                "implementation": [
                    "Create a module-by-module checklist for submission readiness.",
                    "Link each quality claim to supporting method validation and stability evidence.",
                ],
                "latest_updates": ["Track ICH assembly and working group updates for M4 and Q-series revisions."],
                "sources": ["https://www.ich.org/page/multidisciplinary-guidelines", "https://www.ich.org/page/quality-guidelines"],
            }

        if auth == "FDA" or "fda" in q:
            return {
                "title": "FDA regulatory guidance summary",
                "guidelines": ["21 CFR Part 312", "21 CFR Part 314", "351(k) biosimilar pathway"],
                "requirements": ["Map clinical, CMC, and labeling evidence to relevant CFR and guidance expectations."],
                "implementation": ["Use pre-submission meetings to de-risk major evidence gaps."],
                "latest_updates": ["Prioritize newly published FDA guidance documents for your product class."],
                "sources": ["https://www.fda.gov"],
            }

        if auth == "EMA" or "ema" in q:
            return {
                "title": "EMA regulatory guidance summary",
                "guidelines": ["EU CTD format", "EMA scientific guidelines", "CTR (EU) 536/2014 where applicable"],
                "requirements": ["Align dossier strategy with EMA scientific advice and applicable CHMP guidance."],
                "implementation": ["Plan evidence package to meet centralized procedure expectations."],
                "latest_updates": ["Track EMA guideline revisions and committee highlights relevant to product type."],
                "sources": ["https://www.ema.europa.eu"],
            }

        return {
            "title": "Regulatory guidance summary",
            "guidelines": ["Authority-specific primary guideline for the requested topic", "Applicable submission pathway requirements", "Relevant quality/safety/efficacy framework for the query scope"],
            "requirements": ["Map quality, safety, efficacy requirements to authority-specific submission pathways."],
            "implementation": ["Maintain a traceable compliance matrix from guideline to dossier section."],
            "latest_updates": ["Prioritize the most recent authority publication date and effective scope."],
            "sources": ["Regulatory authority publications"],
        }

    def _build_structured_response(
        self,
        title: str,
        guidelines: list[str],
        requirements: list[str],
        implementation: list[str],
        latest_updates: list[str],
        sources: list[str],
    ) -> str:
        def _list(items: list[str], bullet: str = "-") -> str:
            if not items:
                return f"{bullet} Not available"
            return "\n".join([f"{bullet} {item}" for item in items])

        numbered_updates = "\n".join([f"{i + 1}. {item}" for i, item in enumerate(latest_updates or ["Best current guidance has been provided based on available evidence."])])

        return (
            f"Title: {title}\n\n"
            f"Specific Guidelines:\n{_list(guidelines)}\n\n"
            f"Key Requirements:\n{_list(requirements)}\n\n"
            f"Practical Implementation:\n{_list(implementation)}\n\n"
            f"Latest Updates:\n{numbered_updates}\n\n"
            f"Sources:\n{_list(sources)}"
        )

    def _build_rag_prompt(
        self,
        query: str,
        context: str,
        authority: Optional[str],
        query_mode: str,
        metrics: Dict[str, Any]
    ) -> str:
        """
        Build prompt for RAG mode (with retrieved documents)
        """
        authority_str = authority if authority else "Multiple authorities"
        num_docs = metrics.get("documents_injected", 0)
        
        prompt = f"""Use this context first and answer naturally.

    Query: {query}
    Detected Authority: {authority_str}
    Query Mode: {query_mode}
    Documents Retrieved: {num_docs}

    Context:
    ---
    {context}
    ---

    Answer with practical regulatory interpretation, specific references where relevant, and region differences only if they help the user."""
        
        return prompt

    def _build_general_prompt(
        self,
        query: str,
        authority: Optional[str],
        query_mode: str
    ) -> str:
        """
        Build prompt for general knowledge mode (no documents)
        """
        authority_str = f" regarding {authority}" if authority else ""
        
        prompt = f"""Query: {query}
    Query Mode: {query_mode}

    No high-confidence document context was retrieved{authority_str}.

    Provide a direct, expert answer using domain knowledge while staying specific to the detected authority. Avoid generic textbook phrasing and avoid cross-authority comparisons unless requested."""
        
        return prompt

    def _generate_fallback_answer(
        self,
        query: str,
        context: str,
        intent: str,
        authority: Optional[str] = None,
        query_mode: str = "standard"
    ) -> str:
        """Generate deterministic structured answer when LLM call cannot be completed."""
        print("[AI SERVICE] Generating deterministic structured fallback response")

        query_lower = query.lower()
        authority_name = authority if authority else "relevant authority"

        if context.strip():
            lines = [line.strip() for line in context.splitlines() if line.strip()]
            condensed = []
            source_urls = []
            for line in lines:
                if line.startswith("Title:") or line.startswith("Authority:") or line.startswith("Date:") or line.startswith("Category:"):
                    condensed.append(line)
                if line.startswith("Source:"):
                    source_urls.append(line.replace("Source:", "").strip())
                if len(condensed) >= 8:
                    break

            pack = self._domain_guideline_pack(query, authority)
            guidelines = pack.get("guidelines", [])
            requirements = pack.get("requirements", [])
            implementation = pack.get("implementation", [])
            latest_updates = pack.get("latest_updates", [])

            if condensed:
                requirements = condensed[:4] + requirements

            actionable = [
                "Translate key guidance into submission and lifecycle control actions.",
                "Assign owners and timelines for implementation readiness.",
            ]
            implementation = implementation + actionable
            sources = source_urls if source_urls else [f"Retrieved context for {authority_name}"]
            return self._build_structured_response(
                title=pack.get("title", f"{authority_name} regulatory guidance overview"),
                guidelines=guidelines,
                requirements=requirements[:6],
                implementation=implementation[:5],
                latest_updates=latest_updates,
                sources=sources,
            )

        if "biosimilar" in query_lower or "biosimilar" in query_lower:
            prefix = f"No recent {authority}-specific updates found. Here is the most relevant current guidance:\n\n" if query_mode == "latest" and authority else ""
            guidelines = [
                "Biosimilar assessment follows a totality-of-evidence approach with analytical similarity as the foundation.",
                "FDA 351(k) pathway emphasizes residual uncertainty reduction through targeted nonclinical and clinical evidence.",
                "Comparability principles such as ICH Q5E are practical for post-change similarity logic.",
            ]
            latest_updates = [
                f"{authority_name} latest biosimilar guidance should be prioritized by publication year and scope.",
            ]
            implementation = [
                "Build the development plan around analytical comparability first.",
                "Justify any reduced clinical package with explicit residual uncertainty rationale.",
            ]
            requirements = [
                "Demonstrate analytical similarity with predefined critical quality attributes.",
                "Address residual uncertainty with targeted nonclinical/clinical evidence.",
            ]
            sources = [f"{authority_name} biosimilar guidance framework"]
            title = "Biosimilar guidance summary"
            if prefix:
                latest_updates.insert(0, prefix.strip())
            return self._build_structured_response(title, guidelines, requirements, implementation, latest_updates, sources)

        if "stability" in query_lower or "zone iv" in query_lower:
            return self._build_structured_response(
                title="Stability guideline implementation summary",
                guidelines=["ICH Q1A(R2)", "ICH Q1B", "ICH Q1E"],
                requirements=[
                    "Define long-term and accelerated conditions aligned to product and climatic zone strategy.",
                    "Use trend analysis and specification justification in stability protocols.",
                ],
                implementation=[
                    "Link stability outcomes to shelf-life and storage statement decisions.",
                    "Validate packaging configuration under stress and transport-relevant conditions.",
                ],
                latest_updates=["Apply the latest authority interpretation notes for stability expectations in submission reviews."],
                sources=[f"{authority_name} stability guidance"],
            )

        if "clinical trial" in query_lower or "gcp" in query_lower:
            return self._build_structured_response(
                title="Clinical trial compliance framework",
                guidelines=["ICH E6(R2/R3)", "21 CFR Part 50", "21 CFR Part 56", "21 CFR Part 312"],
                requirements=[
                    "Maintain GCP-compliant informed consent, IRB/EC oversight, and safety reporting controls.",
                    "Implement risk-based quality management across study lifecycle.",
                ],
                implementation=[
                    "Define protocol deviation governance and CAPA workflow before first patient in.",
                    "Align vendor oversight and pharmacovigilance interfaces with inspection-readiness evidence.",
                ],
                latest_updates=["Use the latest operational transition guidance for ICH E6 modernization."],
                sources=[f"{authority_name} clinical trial guidance"],
            )

        if query_mode == "latest" and authority:
            pack = self._domain_guideline_pack(query, authority)
            return self._build_structured_response(
                title=pack["title"],
                guidelines=pack["guidelines"],
                requirements=pack["requirements"],
                implementation=pack["implementation"],
                latest_updates=pack["latest_updates"],
                sources=pack["sources"],
            )

        return self._build_structured_response(
            title="Regulatory guidance summary",
            guidelines=["ICH Q1A(R2)", "ICH Q2(R2)", "ICH Q8(R2)"],
            requirements=[
                f"Query scope: {query}",
                "Identify governing regulations and authority-specific implementation requirements.",
                "Prioritize obligations that affect submission content, CMC controls, labeling, and post-approval commitments.",
            ],
            implementation=[
                "Convert guidance requirements into a compliance action plan with owners and timelines.",
                "Prepare evidence artifacts for audit and submission readiness.",
            ],
            latest_updates=["Use the most recently available authority guidance and policy updates relevant to this topic."],
            sources=[f"{authority_name} regulatory framework"],
        )

    def analyze_update(
        self,
        update_title: str,
        update_summary: str,
        full_text: str,
        difficulty_level: str = "professional"
    ) -> dict:
        """
        Generates compliance-focused analysis of a regulatory update using Groq.
        
        Args:
            update_title: Title of the regulatory update
            update_summary: Short summary of the update
            full_text: Full text content of the update
            difficulty_level: One of "beginner", "professional", or "legal"
            
        Returns:
            dict with keys: "summary" (str), "action_items" (list[str]), "risk_level" (str)
        """
        print(f"[AI SERVICE] Analyzing update with level: {difficulty_level}")
        
        # Determine system prompt based on difficulty level
        system_prompts = {
            "beginner": """You are a pharmaceutical regulatory compliance analyst.

Analyze the provided regulatory update and prepare a summary for executive management.

Requirements:
- Use non-technical language suitable for C-level executives
- Focus on business and operational impact
- Maximum 150 words
- Extract 3-4 clear, actionable compliance steps
- Identify key deadlines and affected departments
- Avoid regulatory jargon; explain terms clearly if used
- Format: Start with impact statement, then action items""",
            
            "professional": """You are a pharmaceutical regulatory compliance analyst.

Analyze the provided regulatory update for compliance professionals.

Requirements:
- Provide detailed regulatory analysis (150-200 words)
- Highlight specific compliance requirements and obligations
- Extract 4-5 actionable compliance steps with measurable outcomes
- Identify impacted processes and systems
- Reference relevant regulatory frameworks (FDA, ICH, etc.) where applicable
- Focus on implementation timeline and resource requirements
- Avoid filler language; be analytical and precise""",
            
            "legal": """You are a pharmaceutical regulatory compliance analyst specializing in legal risk.

Analyze the provided regulatory update for legal and compliance teams.

Requirements:
- Provide comprehensive legal and regulatory analysis (150-200 words)
- Identify legal obligations, liability implications, and enforcement risks
- Extract 5 specific legal/compliance action items with remediation steps
- Highlight potential penalty clauses and non-compliance consequences
- Reference applicable regulations and enforcement history
- Include risk mitigation and documentation requirements
- Be precise, analytical, and legally sound"""
        }
        
        system_prompt = system_prompts.get(difficulty_level, system_prompts["professional"])
        
        # Prepare the content to analyze
        content = f"""REGULATORY UPDATE:

Title: {update_title}

Summary: {update_summary}

Full Details: {full_text[:2000]}

Based on this regulatory update, provide:
1. A concise compliance summary (150-200 words)
2. A JSON array of action items
3. Risk level: 'Low', 'Medium', or 'High'

Format your response as:
SUMMARY: [compliance summary]
ACTION_ITEMS: ["item1", "item2", ...]
RISK_LEVEL: [High/Medium/Low]"""
        
        # Try to use Groq if available
        if self.client:
            try:
                print(f"[AI SERVICE] Calling Groq for update analysis...")
                response = self.client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": content}
                    ],
                    temperature=0.5,
                    max_tokens=1000,
                )
                result_text = response.choices[0].message.content
                print(f"[AI SERVICE] Groq analysis response received, parsing...")
                return self._parse_analysis_response(result_text, difficulty_level)
            except Exception as e:
                print(f"[AI SERVICE] Groq error: {e}, using mock response")
                import traceback
                traceback.print_exc()
        
        # Fall back to high-quality mock responses
        print(f"[AI SERVICE] No Groq client, using mock analysis")
        return self._generate_mock_analysis(update_title, update_summary, difficulty_level)

    def _parse_analysis_response(self, response_text: str, difficulty_level: str) -> dict:
        """Parse the structured response from LLM."""
        try:
            summary = ""
            action_items = []
            risk_level = "Medium"
            
            # Extract summary
            if "SUMMARY:" in response_text:
                summary_start = response_text.find("SUMMARY:") + 8
                summary_end = response_text.find("ACTION_ITEMS:")
                if summary_end == -1:
                    summary_end = len(response_text)
                summary = response_text[summary_start:summary_end].strip()
            
            # Extract action items
            if "ACTION_ITEMS:" in response_text:
                items_start = response_text.find("ACTION_ITEMS:") + 13
                items_end = response_text.find("RISK_LEVEL:")
                if items_end == -1:
                    items_end = len(response_text)
                items_text = response_text[items_start:items_end].strip()
                # Parse JSON array
                import json
                try:
                    action_items = json.loads(items_text)
                    if isinstance(action_items, dict):
                        action_items = [f"{k}: {v}" for k, v in action_items.items()]
                except:
                    # Fallback: split by commas or newlines
                    action_items = [
                        item.strip().strip('"').strip('-').strip('•').strip()
                        for item in items_text.replace('\n', ',').split(',')
                        if item.strip()
                    ][:5]
            
            # Extract risk level
            if "RISK_LEVEL:" in response_text:
                risk_start = response_text.find("RISK_LEVEL:") + 11
                risk_text = response_text[risk_start:].split('\n')[0].strip()
                if "high" in risk_text.lower():
                    risk_level = "High"
                elif "low" in risk_text.lower():
                    risk_level = "Low"
                else:
                    risk_level = "Medium"
            
            return {
                "summary": summary if summary else response_text[:500],
                "action_items": action_items[:5] if action_items else ["Review full update", "Assess impact", "Implement changes"],
                "risk_level": risk_level
            }
        except Exception as e:
            print(f"[AI SERVICE] Parse error: {e}")
            return {
                "summary": response_text[:400],
                "action_items": ["Review full update", "Assess impact", "Implement changes"],
                "risk_level": "Medium"
            }

    def _generate_mock_analysis(self, title: str, summary: str, difficulty_level: str) -> dict:
        """Generate high-quality mock analysis when LLM is unavailable."""
        title_lower = title.lower()
        summary_lower = summary.lower()
        combined_text = f"{title_lower} {summary_lower}"
        
        # Detect update type and severity
        is_approval = "approv" in combined_text or "approved" in combined_text
        is_safety = "safety" in combined_text or "adverse" in combined_text or "risk" in combined_text
        is_manufacturing = "manufacturing" in combined_text or "facility" in combined_text or "gmp" in combined_text
        is_urgent = "recall" in combined_text or "urgent" in combined_text or "immediate" in combined_text
        
        risk_level = "High" if (is_safety and is_urgent) or "recall" in combined_text else ("Medium" if is_safety or is_manufacturing else "Low")
        
        if difficulty_level == "beginner":
            if is_approval:
                return {
                    "summary": "A new product or indication has received regulatory approval. The organization should review the approved product characteristics, monitor market entry, and assess competitive impacts. Key stakeholders should be briefed on implications for current product portfolios and strategy.",
                    "action_items": ["Brief executive team on approval", "Monitor market availability", "Update competitive analysis"],
                    "risk_level": "Low"
                }
            elif is_safety:
                return {
                    "summary": "A safety issue has been identified with a regulatory product. Immediate review of company products and manufacturing is required to ensure compliance. If applicable, corrective actions must be implemented promptly to protect patient safety and maintain regulatory standing.",
                    "action_items": ["Evaluate company product exposure", "Assess manufacturing processes", "Implement corrective actions", "Report to regulatory authorities if required"],
                    "risk_level": risk_level
                }
            else:
                return {
                    "summary": "The regulatory authority has issued new guidance or requirements. Compliance is mandatory. The organization must review requirements, assess current practices, and implement necessary changes within regulatory timeframes to remain compliant.",
                    "action_items": ["Review new requirements", "Assess current compliance", "Develop implementation plan"],
                    "risk_level": "Medium"
                }
        
        elif difficulty_level == "professional":
            if is_approval:
                return {
                    "summary": "Regulatory authority has approved a new product or therapeutic indication. This marks a significant milestone in development and market access. The approval decision defines approved indications, patient populations, dosing regimens, and postapproval commitments. Organizations should conduct comprehensive competitive and market analysis, establish pharmacovigilance monitoring, and coordinate commercial, medical, and regulatory strategies for product launch and lifecycle management.",
                    "action_items": [
                        "Conduct expedited competitive benchmarking and market opportunity assessment",
                        "Establish pharmacovigilance and adverse event monitoring systems",
                        "Ensure labeling compliance and promotional material review",
                        "Develop risk management and post-approval commitment fulfillment plans",
                        "Coordinate cross-functional launch strategy and timeline"
                    ],
                    "risk_level": "Low"
                }
            elif is_safety:
                return {
                    "summary": "Regulatory authority has identified a safety signal, adverse event pattern, or manufacturing compliance concern. Depending on severity, may trigger recalls, import alerts, or mandatory corrective actions. Organizations must immediately assess exposure to affected products, manufacturing batches, and suppliers. Comprehensive risk assessment is required to determine evidence strength, affected patient populations, and required interventions.",
                    "action_items": [
                        "Conduct immediate inventory assessment and traceability review for affected products",
                        "Perform comprehensive safety and efficacy data review for company products",
                        "Evaluate manufacturing controls and implement enhanced quality monitoring",
                        "Develop and execute remediation plan with regulatory timeline expectations",
                        "Submit adverse event reports and corrective action notifications as required"
                    ],
                    "risk_level": risk_level
                }
            else:
                return {
                    "summary": "Regulatory authority has issued updated guidance, policy, or requirements. Compliance is mandatory and must be demonstrated upon inspection or audit. Organizations should conduct gap analysis of current practices against new requirements, prioritize implementation based on regulatory enforcement timing, and develop comprehensive compliance strategy.",
                    "action_items": [
                        "Perform detailed compliance gap analysis against new regulatory requirements",
                        "Prioritize implementation based on regulatory enforcement priorities and timelines",
                        "Develop comprehensive standard operating procedure updates",
                        "Implement staff training and competency verification programs",
                        "Establish internal audit and compliance verification processes"
                    ],
                    "risk_level": "Medium"
                }
        
        else:  # legal
            if is_approval:
                return {
                    "summary": "Regulatory authority approval establishes legal authorization for product manufacture, distribution, and marketing within specific approved parameters. Approval defines the legal scope of permissible claims, indications, and patient populations. Organizations must maintain strict compliance with approved labeling and promotional restrictions to avoid regulatory action.",
                    "action_items": [
                        "Establish legal and compliance framework for approved indication and labeling restrictions",
                        "Implement promotional material governance and pre-approval review procedures",
                        "Develop legal documentation standards for all marketing and distribution activities",
                        "Establish liability management and insurance requirements",
                        "Create audit and monitoring procedures to ensure ongoing compliance with approval terms"
                    ],
                    "risk_level": "Low"
                }
            elif is_safety:
                return {
                    "summary": "Safety concerns trigger multiple legal and compliance obligations: mandatory reporting to regulatory authorities, potential product liability exposure, informed consent and disclosure requirements. All safety findings must be immediately documented and reported; failure to report constitutes additional regulatory violations and increases legal exposure.",
                    "action_items": [
                        "Immediately document all safety findings and establish evidence preservation procedures",
                        "Assess legal liability exposure and notification obligations to patients/providers",
                        "File required adverse event reports and safety notifications within regulatory timeframes",
                        "Coordinate with legal counsel on litigation risk assessment and insurance notification",
                        "Implement remediation procedures if product recall or corrective action is required"
                    ],
                    "risk_level": "High"
                }
            else:
                return {
                    "summary": "Regulatory guidance establishes authorities' enforcement expectations and creates legal obligations for industry compliance. Non-compliance creates multiple legal risks: regulatory enforcement action, warning letters, consent decrees, civil money penalties, and product seizures. Organizations must establish legal compliance documentation and demonstrate adherence to regulatory requirements.",
                    "action_items": [
                        "Establish written legal compliance policies reflecting regulatory guidance requirements",
                        "Certify organizational compliance through documented management review and attestation",
                        "Implement legal audit and surveillance procedures with professional documentation",
                        "Establish regulatory liaison and legal reporting procedures for non-compliance discovery",
                        "Maintain compliance records and establish legal defense preparedness"
                    ],
                    "risk_level": "Medium"
                }


# Global instance
ai_service = AIService()
