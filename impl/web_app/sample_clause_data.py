"""
Sample clause data for testing Clause Library Phase 2 functionality.

This script provides realistic legal clauses for testing:
- AI comparison accuracy
- Vector search quality
- Embedding optimization
- Performance monitoring
"""

SAMPLE_CLAUSES = [
    {
        "name": "Standard Mutual Indemnification",
        "description": "Mutual indemnification clause with broad coverage for both parties",
        "category_id": "indemnification_mutual_broad",
        "content_html": """
            <p>Each party (the "<span class="variable" data-var="INDEMNIFYING_PARTY">Indemnifying Party</span>")
            shall indemnify, defend, and hold harmless the other party (the "<span class="variable" data-var="INDEMNIFIED_PARTY">Indemnified Party</span>"),
            its affiliates, and their respective officers, directors, employees, and agents from and against any and all
            claims, demands, losses, liabilities, damages, costs, and expenses (including reasonable attorneys' fees and
            court costs) arising out of or relating to:</p>
            <ul>
                <li>Any breach of this Agreement by the Indemnifying Party;</li>
                <li>Any negligent acts or omissions or willful misconduct by the Indemnifying Party;</li>
                <li>Any infringement or alleged infringement of any intellectual property rights by the Indemnifying Party;</li>
                <li>Any violation of applicable laws or regulations by the Indemnifying Party.</li>
            </ul>
            <p>The Indemnified Party shall provide the Indemnifying Party with prompt written notice of any claim and
            shall cooperate with the Indemnifying Party in the defense of such claim.</p>
        """,
        "tags": ["indemnification", "liability", "mutual", "broad-coverage"],
        "contract_types": ["MSA", "SOW", "Service Agreement"],
        "jurisdictions": ["multi-state", "federal"],
        "risk_level": "medium",
        "complexity": "high"
    },
    {
        "name": "Limited Indemnification - Contractor Liability Only",
        "description": "One-way indemnification with contractor assuming liability",
        "category_id": "indemnification_limited",
        "content_html": """
            <p><span class="variable" data-var="CONTRACTOR_PARTY">Contractor</span> shall indemnify and hold harmless
            <span class="variable" data-var="CONTRACTING_PARTY">Client</span> from and against any claims, losses, or
            damages arising from Contractor's performance under this Agreement, excluding any claims arising from
            Client's specifications or directions.</p>
            <p>The total liability of Contractor under this indemnification shall not exceed the total fees paid under
            this Agreement in the twelve (12) months preceding the claim.</p>
        """,
        "tags": ["indemnification", "liability", "one-way", "limited"],
        "contract_types": ["SOW", "Independent Contractor"],
        "jurisdictions": ["multi-state"],
        "risk_level": "low",
        "complexity": "medium"
    },
    {
        "name": "Standard Confidentiality Clause",
        "description": "Mutual confidentiality obligations with standard exceptions",
        "category_id": "confidentiality_mutual",
        "content_html": """
            <p>Each party (the "<strong>Receiving Party</strong>") acknowledges that it may receive confidential and
            proprietary information from the other party (the "<strong>Disclosing Party</strong>") during the term of
            this Agreement. The Receiving Party agrees to:</p>
            <ol>
                <li>Maintain the confidentiality of all Confidential Information;</li>
                <li>Use the Confidential Information solely for the purposes contemplated by this Agreement;</li>
                <li>Not disclose Confidential Information to any third party without prior written consent;</li>
                <li>Protect the Confidential Information with the same degree of care used to protect its own confidential information, but no less than reasonable care.</li>
            </ol>
            <p><strong>Exceptions:</strong> Confidential Information does not include information that:</p>
            <ul>
                <li>Is or becomes publicly available through no breach of this Agreement;</li>
                <li>Was rightfully known to the Receiving Party prior to disclosure;</li>
                <li>Is rightfully received from a third party without breach of confidentiality obligations;</li>
                <li>Is independently developed without use of the Confidential Information.</li>
            </ul>
            <p>These obligations shall survive termination for a period of <span class="variable" data-var="CONFIDENTIALITY_TERM">three (3) years</span>.</p>
        """,
        "tags": ["confidentiality", "NDA", "mutual", "proprietary"],
        "contract_types": ["MSA", "NDA", "SOW"],
        "jurisdictions": ["multi-state", "federal"],
        "risk_level": "medium",
        "complexity": "high"
    },
    {
        "name": "Standard Payment Terms - Net 30",
        "description": "Standard payment terms with net 30 day payment period",
        "category_id": "payment_terms",
        "content_html": """
            <p><span class="variable" data-var="CONTRACTING_PARTY">Client</span> shall pay
            <span class="variable" data-var="CONTRACTOR_PARTY">Contractor</span> the fees set forth in Exhibit A.</p>
            <p>Payment terms are Net 30 days from the date of invoice. Invoices shall be submitted monthly and shall
            include a detailed description of services rendered.</p>
            <p><strong>Late Payments:</strong> Any payment not received within thirty (30) days of the invoice date
            shall accrue interest at the rate of 1.5% per month or the maximum rate permitted by law, whichever is less.</p>
            <p><strong>Disputed Invoices:</strong> Client must notify Contractor in writing of any disputed charges
            within ten (10) days of receiving an invoice. Undisputed amounts shall be paid in accordance with the
            payment terms.</p>
        """,
        "tags": ["payment", "net-30", "invoicing", "late-fees"],
        "contract_types": ["MSA", "SOW", "Service Agreement"],
        "jurisdictions": ["multi-state"],
        "risk_level": "low",
        "complexity": "medium"
    },
    {
        "name": "Termination for Convenience",
        "description": "Allows either party to terminate without cause with notice",
        "category_id": "termination",
        "content_html": """
            <p>Either party may terminate this Agreement for convenience upon
            <span class="variable" data-var="TERMINATION_NOTICE_DAYS">thirty (30) days</span> prior written notice to
            the other party.</p>
            <p>Upon termination for convenience, <span class="variable" data-var="CONTRACTING_PARTY">Client</span> shall
            pay <span class="variable" data-var="CONTRACTOR_PARTY">Contractor</span> for all services performed and
            expenses incurred up to the effective date of termination.</p>
            <p>Sections related to confidentiality, indemnification, limitation of liability, and dispute resolution
            shall survive termination of this Agreement.</p>
        """,
        "tags": ["termination", "convenience", "notice"],
        "contract_types": ["MSA", "SOW"],
        "jurisdictions": ["multi-state"],
        "risk_level": "low",
        "complexity": "low"
    },
    {
        "name": "Limitation of Liability - Cap and Exclusions",
        "description": "Limits liability with cap and excludes consequential damages",
        "category_id": "indemnification",  # Using indemnification as liability is closely related
        "content_html": """
            <p><strong>Cap on Liability:</strong> Except for breaches of confidentiality obligations or indemnification
            obligations, the total aggregate liability of either party under this Agreement shall not exceed the total
            fees paid or payable under this Agreement in the twelve (12) months preceding the claim.</p>
            <p><strong>Exclusion of Consequential Damages:</strong> In no event shall either party be liable for any
            indirect, incidental, special, consequential, or punitive damages, including but not limited to loss of
            profits, loss of revenue, loss of data, or business interruption, regardless of the theory of liability,
            even if advised of the possibility of such damages.</p>
            <p><strong>Exceptions:</strong> The limitations set forth in this section shall not apply to:</p>
            <ul>
                <li>Breaches of confidentiality obligations;</li>
                <li>Indemnification obligations;</li>
                <li>Gross negligence or willful misconduct;</li>
                <li>Violations of intellectual property rights.</li>
            </ul>
        """,
        "tags": ["liability", "limitation", "cap", "consequential-damages"],
        "contract_types": ["MSA", "Service Agreement"],
        "jurisdictions": ["multi-state"],
        "risk_level": "medium",
        "complexity": "high"
    },
    {
        "name": "Intellectual Property - Work for Hire",
        "description": "All work product is owned by client as work for hire",
        "category_id": "intellectual_property",
        "content_html": """
            <p><strong>Ownership of Work Product:</strong> All work product, deliverables, inventions, discoveries,
            and intellectual property created by <span class="variable" data-var="CONTRACTOR_PARTY">Contractor</span>
            in connection with this Agreement (collectively, "<strong>Work Product</strong>") shall be considered "work
            made for hire" under applicable copyright law and shall be owned exclusively by
            <span class="variable" data-var="CONTRACTING_PARTY">Client</span>.</p>
            <p>To the extent any Work Product does not qualify as work made for hire, Contractor hereby assigns to
            Client all right, title, and interest in and to such Work Product, including all intellectual property
            rights therein.</p>
            <p><strong>Pre-Existing Materials:</strong> Contractor retains all rights to any pre-existing materials,
            tools, or intellectual property developed prior to this Agreement. Contractor grants Client a perpetual,
            non-exclusive, royalty-free license to use such pre-existing materials to the extent incorporated into
            the Work Product.</p>
        """,
        "tags": ["intellectual-property", "work-for-hire", "ownership", "copyright"],
        "contract_types": ["SOW", "Development Agreement"],
        "jurisdictions": ["federal"],
        "risk_level": "high",
        "complexity": "high"
    },
    {
        "name": "Force Majeure",
        "description": "Excuses performance during events beyond parties' control",
        "category_id": "termination",  # Force majeure can lead to termination
        "content_html": """
            <p>Neither party shall be liable for any failure or delay in performance under this Agreement to the extent
            such failure or delay is caused by circumstances beyond the reasonable control of such party, including but
            not limited to:</p>
            <ul>
                <li>Acts of God, natural disasters, or severe weather;</li>
                <li>War, terrorism, civil unrest, or government action;</li>
                <li>Pandemics, epidemics, or public health emergencies;</li>
                <li>Labor disputes or strikes;</li>
                <li>Failures of public utilities or communication systems;</li>
                <li>Fire, explosion, or other catastrophic events.</li>
            </ul>
            <p>The affected party shall provide prompt written notice to the other party and shall use commercially
            reasonable efforts to minimize the impact and resume performance as soon as reasonably practicable.</p>
            <p>If a force majeure event continues for more than <span class="variable" data-var="FORCE_MAJEURE_TERMINATION_DAYS">sixty (60) days</span>,
            either party may terminate this Agreement upon written notice without liability.</p>
        """,
        "tags": ["force-majeure", "acts-of-god", "excusable-delay"],
        "contract_types": ["MSA", "SOW", "Service Agreement"],
        "jurisdictions": ["multi-state"],
        "risk_level": "low",
        "complexity": "medium"
    }
]


# Test scenarios for comparison accuracy
COMPARISON_TEST_CASES = [
    {
        "clause_name": "Standard Mutual Indemnification",
        "contract_text": """Each party shall indemnify and defend the other party from any claims arising from
        its breach of this agreement or negligent acts. Notice must be provided promptly.""",
        "expected_similarity": "high",  # 0.7-0.9
        "expected_risks": ["missing coverage for IP infringement", "missing coverage for law violations"],
        "description": "Simplified version with key elements but missing some protections"
    },
    {
        "clause_name": "Standard Confidentiality Clause",
        "contract_text": """The receiving party will keep confidential information secret and not disclose it
        to third parties. This obligation lasts for 5 years after termination.""",
        "expected_similarity": "medium",  # 0.5-0.7
        "expected_risks": ["missing standard exceptions", "different confidentiality term"],
        "description": "Basic confidentiality with longer term but missing exceptions"
    },
    {
        "clause_name": "Standard Payment Terms - Net 30",
        "contract_text": """Client will pay Contractor within 45 days of invoice. Late payments incur 2% monthly interest.""",
        "expected_similarity": "high",  # 0.7-0.9
        "expected_risks": ["longer payment period", "higher late fee rate"],
        "description": "Similar payment structure but different terms"
    },
    {
        "clause_name": "Limitation of Liability - Cap and Exclusions",
        "contract_text": """Neither party is liable for consequential damages. Total liability is capped at fees paid.""",
        "expected_similarity": "medium",  # 0.5-0.7
        "expected_risks": ["missing exceptions", "unclear cap calculation period"],
        "description": "Has key concepts but missing important details"
    },
    {
        "clause_name": "Intellectual Property - Work for Hire",
        "contract_text": """All deliverables created under this agreement are owned by Client.""",
        "expected_similarity": "low",  # 0.3-0.5
        "expected_risks": ["no work for hire language", "missing assignment clause", "no pre-existing materials handling"],
        "description": "Very simplified ownership clause missing critical legal protections"
    }
]


def get_sample_clauses():
    """Get list of sample clauses for database population."""
    return SAMPLE_CLAUSES


def get_test_cases():
    """Get test cases for comparison accuracy testing."""
    return COMPARISON_TEST_CASES
