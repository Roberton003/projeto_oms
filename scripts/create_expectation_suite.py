import great_expectations as gx
import os

# Get the absolute path to the great_expectations directory
context_root_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'great_expectations')

# Load the data context
context = gx.get_context(context_root_dir=context_root_dir)

# Create an expectation suite
context.add_expectation_suite(expectation_suite_name="fact_observations_suite")

print("Expectation suite 'fact_observations_suite' created successfully.")