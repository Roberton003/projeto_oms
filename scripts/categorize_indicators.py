
import pandas as pd
import os

def categorize_indicators(file_path):
    """
    Reads the indicators.csv file and categorizes the indicators based on their codes.
    """
    try:
        df = pd.read_csv(file_path)
        # Extract the first part of the indicator code as the category
        df['Category'] = df['IndicatorCode'].apply(lambda x: x.split('_')[0])
        
        # Get the category counts
        category_counts = df['Category'].value_counts()
        
        print("Top 20 Indicator Categories:")
        print(category_counts.head(20))
        
        # Save the categorized indicators to a new CSV file
        # Correcting the output path to be relative to the project root, not the script's location.
        # This assumes the script is run from the project root.
        output_path = os.path.join('data', 'categorized_indicators.csv')
        df.to_csv(output_path, index=False)
        print(f"\nCategorized indicators saved to: {output_path}")
        
    except FileNotFoundError:
        print(f"Error: The file {file_path} was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # The script is expected to be run from the project root directory
    file_path = os.path.join('data', 'indicators.csv')
    categorize_indicators(file_path)
