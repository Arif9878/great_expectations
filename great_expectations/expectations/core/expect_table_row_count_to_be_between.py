from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd

from great_expectations.core.batch import Batch
from great_expectations.core.expectation_configuration import ExpectationConfiguration
from great_expectations.execution_engine import ExecutionEngine, PandasExecutionEngine

from ...data_asset.util import parse_result_format
from ..expectation import (
    DatasetExpectation,
    Expectation,
    InvalidExpectationConfigurationError,
    _format_map_output,
)
from ..registry import extract_metrics


class ExpectTableRowCountToBeBetween(DatasetExpectation):
    """Expect the number of rows to be between two values.

    expect_table_row_count_to_be_between is a :func:`expectation \
    <great_expectations.validator.validator.Validator.expectation>`, not a
    ``column_map_expectation`` or ``column_aggregate_expectation``.

    Keyword Args:
        min_value (int or None): \
            The minimum number of rows, inclusive.
        max_value (int or None): \
            The maximum number of rows, inclusive.

    Other Parameters:
        result_format (str or None): \
            Which output mode to use: `BOOLEAN_ONLY`, `BASIC`, `COMPLETE`, or `SUMMARY`.
            For more detail, see :ref:`result_format <result_format>`.
        include_config (boolean): \
            If True, then include the expectation config as part of the result object. \
            For more detail, see :ref:`include_config`.
        catch_exceptions (boolean or None): \
            If True, then catch exceptions and include them as part of the result object. \
            For more detail, see :ref:`catch_exceptions`.
        meta (dict or None): \
            A JSON-serializable dictionary (nesting allowed) that will be included in the output without \
            modification. For more detail, see :ref:`meta`.

    Returns:
        An ExpectationSuiteValidationResult

        Exact fields vary depending on the values passed to :ref:`result_format <result_format>` and
        :ref:`include_config`, :ref:`catch_exceptions`, and :ref:`meta`.

    Notes:
        * min_value and max_value are both inclusive.
        * If min_value is None, then max_value is treated as an upper bound, and the number of acceptable rows has \
          no minimum.
        * If max_value is None, then min_value is treated as a lower bound, and the number of acceptable rows has \
          no maximum.

    See Also:
        expect_table_row_count_to_equal
    """

    metric_dependencies = ("column_values.count",)
    success_keys = (
        "min_value",
        "max_value",
        "mostly",
    )

    default_kwarg_values = {
        "row_condition": None,
        "condition_parser": None,  # we expect this to be explicitly set whenever a row_condition is passed
        "mostly": 1,
        "min_value": None,
        "max_value": None,
        "result_format": "BASIC",
        "include_config": True,
        "catch_exceptions": False,
        "meta": None,
    }

    """ A Map Metric Decorator for the Row Count"""
    # TODO: Confirm - given that this uses the same metric as expect_table_row_count_to_equal, is it ok to have this
    #    expectation without any metrics?
    # @PandasExecutionEngine.metric(
    #     metric_name="rows.count",
    #     metric_domain_keys=DatasetExpectation.domain_keys,
    #     metric_value_keys=(),
    #     metric_dependencies=tuple(),
    #     filter_column_isnull=False
    # )
    # def _pandas_row_count(
    #     self,
    #     batches: Dict[str, Batch],
    #     execution_engine: PandasExecutionEngine,
    #     metric_domain_kwargs: dict,
    #     metric_value_kwargs: dict,
    #     metrics: dict,
    #     runtime_configuration: dict = None,
    #     filter_column_isnull: bool = False,
    # ):
    #     """Row Count Metric Function"""
    #     df = execution_engine.get_domain_dataframe(
    #         domain_kwargs=metric_domain_kwargs, batches=batches
    #     )
    #
    #     return df.shape[0]

    def validate_configuration(self, configuration: Optional[ExpectationConfiguration]):
        """
        Validates that a configuration has been set, and sets a configuration if it has yet to be set. Ensures that
        neccessary configuration arguments have been provided for the validation of the expectation.

        Args:
            configuration (OPTIONAL[ExpectationConfiguration]): \
                An optional Expectation Configuration entry that will be used to configure the expectation
        Returns:
            True if the configuration has been validated successfully. Otherwise, raises an exception
        """

        # Setting up a configuration
        super().validate_configuration(configuration)
        if configuration is None:
            configuration = self.configuration

        min_val = None
        max_val = None

        # Setting these values if they are available
        if "min_value" in configuration.kwargs:
            min_val = configuration.kwargs["min_value"]

        if "max_value" in configuration.kwargs:
            max_val = configuration.kwargs["max_value"]

        try:
            if min_val is not None:
                if not float(min_val).is_integer():
                    raise ValueError("min_value must be integer")
            if max_val is not None:
                if not float(max_val).is_integer():
                    raise ValueError("max_value must be integer")

        except ValueError:
            raise ValueError("min_value and max_value must be integers")

        return True

    @Expectation.validates(metric_dependencies=metric_dependencies)
    def _validates(
        self,
        configuration: ExpectationConfiguration,
        metrics: dict,
        runtime_configuration: dict = None,
        execution_engine: ExecutionEngine = None,
    ):
        """Validates the given data against the set minimum and maximum value thresholds for the row Count"""
        # Obtaining dependencies used to validate the expectation
        validation_dependencies = self.get_validation_dependencies(
            configuration, execution_engine, runtime_configuration
        )["metrics"]
        # Extracting metrics
        metric_vals = extract_metrics(
            validation_dependencies, metrics, configuration, runtime_configuration
        )

        # Runtime configuration has preference
        if runtime_configuration:
            result_format = runtime_configuration.get(
                "result_format",
                configuration.kwargs.get(
                    "result_format", self.default_kwarg_values.get("result_format")
                ),
            )
        else:
            result_format = configuration.kwargs.get(
                "result_format", self.default_kwarg_values.get("result_format")
            )

        row_count = metric_vals.get("column_values.count")

        # Obtaining components needed for validation
        min_value = self.get_success_kwargs(configuration).get("min_value")
        max_value = self.get_success_kwargs(configuration).get("max_value")

        # Checking if mean lies between thresholds
        if min_value is not None:
            above_min = row_count >= min_value
        else:
            above_min = True

        if max_value is not None:
            below_max = row_count <= max_value
        else:
            below_max = True

        success = above_min and below_max

        return {"success": success, "result": {"observed_value": row_count}}