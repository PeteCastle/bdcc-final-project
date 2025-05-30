import boto3
from botocore.exceptions import ClientError
from typing import TYPE_CHECKING
from dotenv import load_dotenv
import os
from tempfile import NamedTemporaryFile

# if TYPE_CHECKING:
import pandas as pd
import geopandas as gpd

class S3ClientHandler:
    def __init__(self, bucket_name = None):
        load_dotenv()
        self._initialized = True
        self.s3_client = boto3.client("s3")
        

        if bucket_name is None:
            self.bucket_name = os.environ.get('S3_BUCKET_NAME')

            if not self.bucket_name:
                raise ValueError("S3 bucket name not found in environment variables.")
        else:
            self.bucket_name = bucket_name

        self._check_permissions()

    def _check_permissions(self):
        """
        Check if the S3 client has the necessary permissions for the bucket.
        """
        try:
            # Attempt to list objects in the bucket to verify permissions
            self.s3_client.list_objects_v2(Bucket=self.bucket_name, MaxKeys=1)
            print(f"Permissions verified for bucket: {self.bucket_name}")
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "AccessDenied":
                raise PermissionError(f"Access denied to bucket: {self.bucket_name}")
            elif error_code == "NoSuchBucket":
                raise ValueError(f"Bucket does not exist: {self.bucket_name}")
            else:
                raise e
            
    def list_files(self, folder: str = "") -> list:
        """
        List all files in the S3 bucket.
        """
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=folder)
            if "Contents" in response:
                return [obj["Key"] for obj in response["Contents"]]
            else:
                return []
        except ClientError as e:
            print(f"Error listing files: {e}")
            return []

    def get_client(self):
        """
        Return the S3 client instance.
        """
        return self.s3_client
    
    def upload_geodataframe(self, gdf: gpd.GeoDataFrame, file_name: str, folder: str = "amenities") -> None:
        """
        Upload a GeoDataFrame to S3 as a shapefile.
        """
        with NamedTemporaryFile(suffix=".geojson", delete=True) as temp_file:
            try:
                gdf.to_file(temp_file.name, driver="GeoJSON")
                s3_key = f"{folder}/{file_name}.geojson"
                self.s3_client.upload_file(temp_file.name, self.bucket_name, s3_key)
                print(f"Uploaded amenities to s3://{self.bucket_name}/{s3_key}")
            except ClientError as e:
                print(f"Error uploading file: {e}")

    def get_geodataframe(self, file_name: str, folder: str = "amenities") -> gpd.GeoDataFrame:
        """
        Download a GeoDataFrame from S3 as a shapefile.
        """
        with NamedTemporaryFile(suffix=".geojson", delete=True) as temp_file:
            try:
                s3_key = f"{folder}/{file_name}.geojson"
                self.s3_client.download_file(self.bucket_name, s3_key, temp_file.name)
                gdf = gpd.read_file(temp_file.name)
                return gdf
            except ClientError as e:
                print(f"Error downloading file: {e}")
                return None
            
    def get_excel_file(self, file_name: str, folder: str = "amenities") -> pd.DataFrame:
        """
        Download an Excel file from S3 and return it as a DataFrame.
        """
        with NamedTemporaryFile(suffix=".xlsx", delete=True) as temp_file:
            try:
                s3_key = f"{folder}/{file_name}.xlsx"
                self.s3_client.download_file(self.bucket_name, s3_key, temp_file.name)
                df = pd.read_excel(temp_file.name)
                return df
            except ClientError as e:
                print(f"Error downloading file: {e}")
                return None
            
    def check_geodataframe_exists(self, file_name: str, folder: str = "amenities") -> bool:
        """
        Check if a GeoDataFrame exists in S3.
        """
        try:
            s3_key = f"{folder}/{file_name}.geojson"
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            else:
                print(f"Error checking file existence: {e}")
                return False
            
    def check_file_exists(self, file_name: str, folder: str = "") -> bool:
        """
        Check if a file exists in the S3 bucket.
        """
        try:
            s3_key = f"{folder}/{file_name}"
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            else:
                print(f"Error checking file existence: {e}")
                return False
            
    def list_files_with_sizes(self, folder: str = "") -> pd.DataFrame:
        """
        List all files in the S3 bucket along with their sizes and return as a DataFrame.
        """
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=folder)

            data = []
            for page in pages:
                for obj in page.get("Contents", []):
                    data.append({
                        "file_name": obj["Key"],
                        "size_bytes": obj["Size"]
                    })

            return pd.DataFrame(data) if data else pd.DataFrame(columns=["file_name", "size_bytes"])
        except ClientError as e:
            print(f"Error listing files: {e}")
            return pd.DataFrame(columns=["file_name", "size_bytes"])