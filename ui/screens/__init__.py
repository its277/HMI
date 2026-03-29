# ui.screens package
"""Individual HMI screen widgets."""
from .splash_screen import SplashScreen
from .setup_screen import SetupScreen
from .analysis_screen import AnalysisScreen
from .results_screen import ResultsScreen
from .history_screen import HistoryScreen

__all__ = [
    "SplashScreen",
    "SetupScreen",
    "AnalysisScreen",
    "ResultsScreen",
    "HistoryScreen",
]
