from langchain.tools import tool

class LCPFilterTool:

    def extract_lcp_score(report_data):
        # returns the last "end" value in the report_data
        return report_data[-1]["end"]

    @staticmethod
    def extract_lcp_events(report_data):
        # Sort report by start and end times
        sorted_data = sorted(report_data, key=lambda x: (x['start'], x['end']))
        
        # Find the index of the first object with "type": "LCP"
        lcp_index = next((i for i, x in enumerate(sorted_data) if x['type'] == "LCP"), None)
        
        if lcp_index is None:
            return "No LCP event found in the report data."
            
        # Return all objects up to and including LCP
        return sorted_data[:lcp_index + 1]

    @tool("Filter LCP Data")
    def filter_lcp_data(report_data):
        """Filters the performance report data to only include entries up to and including the LCP event.
        Input should be a list of performance report entries.
        Returns the filtered list containing only relevant LCP data."""
        try:
            return LCPFilterTool.extract_lcp_events(report_data)
        except Exception as e:
            return f"Error filtering LCP data: {str(e)}" 