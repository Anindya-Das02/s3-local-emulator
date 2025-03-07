from fastapi import FastAPI, Query, UploadFile, File, HTTPException
import boto3
import os

app = FastAPI(
    title='S3 Local Emulator',
    description="A lightweight, local AWS S3-compatible service powered by LocalStack. Perfect for testing and development, this emulator allows you to simulate S3 operations locally without connecting to the cloud. Test your code, debug workflows, and ensure seamless integration with AWS S3—all from your localmachine.",
    license_info={"name": "MIT License", "url": "https://opensource.org/licenses/MIT"},
    docs_url='/swagger',
    version='1.0.0',
    openapi_tags=[
        {
            "name": "Health Check",
            "description": "Endpoints for checking the health of the service.",
        },
        {
            "name": "S3 Operations",
            "description": "Endpoints for managing localstack S3 buckets and objects.",
        },
    ],
)


# Configure boto3 to use LocalStack
s3 = boto3.client(
    "s3",
    endpoint_url="http://localstack:4566",  # LocalStack endpoint
    aws_access_key_id="test",              # Dummy credentials
    aws_secret_access_key="test",          # Dummy credentials
    region_name="us-east-1"                # Default region
)

@app.get("/health", tags=["Health Check"])
def health_check():
    """
    Health check endpoint to ensure the service is up and running.
    """
    return {"message": "Hello, World!"}

# List all S3 buckets
@app.get("/list-buckets", tags=["S3 Operations"])
def list_buckets():
    """
    List all S3 buckets in the localstack instance.
    """
    try:
        response = s3.list_buckets()
        buckets = [bucket["Name"] for bucket in response["Buckets"]]
        return {"buckets": buckets}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/list-contents/{bucket_name}", tags=["S3 Operations"])
def list_bucket_contents(bucket_name: str):
    """
    List all objects in the specified S3 bucket.
    """
    try:
        response = s3.list_objects_v2(Bucket=bucket_name)
        if "Contents" in response:
            return {"bucket-name" : bucket_name, "objects": [obj["Key"] for obj in response["Contents"]]}
        else:
            return {"message": f"The bucket '{bucket_name}' is empty."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/download/{bucket_name}", tags=["S3 Operations"])
def download_file_or_contents_with_prefix(bucket_name: str, key: str = Query(None, description="Key to download"), prefix: str = Query(None, description="Contents with Prefix to download")):
    """
    Download a file or all files under a prefix from the S3 bucket.
    """
    try:
        if key:
            # Construct the local file path, preserving the folder structure
            local_path = os.path.join(DOWNLOADS_FOLDER, key)
            # Create the local directory if it doesn't exist
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            # Download the file
            download_file(bucket_name, key, local_path)
            return {"message": f"File '{key}' downloaded to '{local_path}' successfully."}
        elif prefix:
            # Download all files under the prefix
            result = download_prefix(bucket_name, prefix)
            return {"message": result}
        else:
            raise HTTPException(status_code=400, detail="Either 'key' or 'prefix' must be provided.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/create-bucket/{bucket_name}", tags=["S3 Operations"])
def create_bucket(bucket_name: str):
    """
    Create an S3 bucket with the specified name if it does not already exist.
    """
    try:
        existing_buckets = s3.list_buckets()["Buckets"]
        bucket_names = [bucket["Name"] for bucket in existing_buckets]
        if bucket_name in bucket_names:
            return {"message": f"Bucket '{bucket_name}' already exists."}
        else:
            # Create the bucket if it doesn't exist
            s3.create_bucket(Bucket=bucket_name)
            return {"message": f"Bucket '{bucket_name}' created successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Upload a file to an S3 bucket
@app.post("/upload-file/{bucket_name}", tags=["S3 Operations"])
async def upload_file(bucket_name: str, folderPath: str = Query(None, description="(Optional)Folder path in the S3 bucket"), file: UploadFile = File(...)):
    """
    Upload a file to the specified S3 bucket.
    """
    try:
        if folderPath:
            folderPath = folderPath.rstrip("/")
            key = f"{folderPath}/{file.filename}"
        else:
            key = file.filename

        if key.startswith("/"):
            key = key[1:]

        s3.upload_fileobj(file.file, bucket_name, key)
        return {"message": f"File '{file.filename}' uploaded successfully! Path:'{bucket_name}/{key}'"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    



@app.post("/create-folders/{bucket_name}", tags=["S3 Operations"])
def create_folders(bucket_name: str, key: str = Query(..., description="Folder path to create in the S3 bucket")):
    """
    Create a folder (key) in the specified S3 bucket.
    """
    try:
        if not key.endswith("/"):
            key += "/"
        s3.put_object(Bucket=bucket_name, Key=key)
        return {"message": f"Folder '{key}' created successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/delete-key/{bucket_name}", tags=["S3 Operations"])
def delete_key_or_file(bucket_name: str, key: str = Query(..., description="Key or Path of the object to delete")):
    """
    Delete an object (file or folder) from the specified S3 bucket.
    """
    try:
        # Delete the object (file) from the bucket
        s3.delete_object(Bucket=bucket_name, Key=key)
        return {"message": f"File '{key}' deleted from bucket '{bucket_name}' successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/delete-contents/{bucket_name}", tags=["S3 Operations"])
def delete_contents_with_prefix(bucket_name: str, prefix: str):
    """
    Delete all objects under a prefix from the specified S3 bucket.
    """
    result = delete_objects_with_prefix(bucket_name, prefix)
    return {"message": result}

@app.delete("/delete-bucket/{bucket_name}", tags=["S3 Operations"])
def delete_bucket(bucket_name: str):
    """
    Delete the specified S3 bucket along with all its contents.
    """
    try:
        delete_objects_with_prefix(bucket_name)
        s3.delete_bucket(Bucket=bucket_name)
        return {"message": f"Bucket '{bucket_name}' deleted successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
def delete_objects_with_prefix(bucket_name: str, prefix: str = ""):
    try:
        if prefix and not prefix.endswith("/"):
            prefix += "/"

        objects_to_delete = []
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
            if "Contents" in page:
                for obj in page["Contents"]:
                    objects_to_delete.append({"Key": obj["Key"]})

        # Delete all objects with the prefix
        if objects_to_delete:
            s3.delete_objects(
                Bucket=bucket_name,
                Delete={"Objects": objects_to_delete}
            )
            return f"All objects under prefix '{prefix}' deleted from bucket '{bucket_name}' successfully."
        else:
            return f"No objects found with prefix '{prefix}' in bucket '{bucket_name}'."
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
DOWNLOADS_FOLDER = "s3_downloads"
if not os.path.exists(DOWNLOADS_FOLDER):
    os.makedirs(DOWNLOADS_FOLDER)

def download_file(bucket_name: str, key: str, local_path: str):
    """
    Download a single file from S3 and save it to the local path.
    """
    try:
        s3.download_file(bucket_name, key, local_path)
        print(f"File '{key}' downloaded to '{local_path}' successfully.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def download_prefix(bucket_name: str, prefix: str):
    """
    Download all files under a prefix from S3 and save them to the local downloads folder,
    maintaining the folder structure.
    """
    try:
        # Ensure the prefix ends with a slash (to match all child keys)
        if prefix and not prefix.endswith("/"):
            prefix += "/"

        # List all objects with the given prefix
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
            if "Contents" in page:
                for obj in page["Contents"]:
                    key = obj["Key"]
                    # Construct the local file path
                    local_path = os.path.join(DOWNLOADS_FOLDER, key)
                    # Create the local directory if it doesn't exist
                    os.makedirs(os.path.dirname(local_path), exist_ok=True)
                    # Download the file
                    download_file(bucket_name, key, local_path)
        return f"All files under prefix '{prefix}' downloaded to '{DOWNLOADS_FOLDER}' successfully."
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8773)