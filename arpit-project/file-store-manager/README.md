# File Store Manager

The service that is responsible for managing file stores in evertz.io
This application is an AWS Serverless project structured in the style recommended by SAM CLI

Currently, We support this FileStore type classes:
    * PLAYLIST_IMPORT
    * CONTENT_SERVICE_ASSET
    * CONTENT_SERVICE_BROWSE
    * CONTENT_SERVICE_TIMELINE
    * CONTENT_SERVICE_HI_RES
    * CONTENT_SERVICE_UPLOADER
    * TAGS
    * ASRUN
    * PLAYLIST_EXPORT
    * DATA_TRANSLATION
    * THUMBNAIL
    * GRACENOTE_EXPORT
    * EPG_EXPORT
    * OUTPUT
    * NAFT_REPORT
    


## API 

```json
{
  "data": {
    "type": "fileStore",
    "attributes": {
      "name": "playlist-import-filestore",
      "description": "Playlist import filestore",
      "storeType": {
        "fileClass": "PLAYLIST_IMPORT",
        "fileFormat": "PXF"
      },
      "bucket": "playlist-pxf-customer-store",
      "folderPrefix": "",
      "accessRoleArn": "arn:aws:iam::537376033299:role/store-cross-account-content-acc-EvertzIOAccessRole-1OL3RQKBQBPQ0"
    }
  }
}
```

We have introduced a new field called "folderPrefix." 

The reason for introducing it is to allow the file-store 
to point one step deeper inside the bucket to the specified folder.
Previously, it only pointed to the root of the bucket. 
We have ensured backward compatibility.

Note: "folderPrefix" is a required field. 
If we don't want to specify it, keep it as an empty string (""). 
An empty string is treated as the root location of the S3 Bucket.

In addition, filestores will contain new fields for name, description, state, and writeable, where
"name" of the filestore is a required field, it should be unique and cannot accept empty string.
"description" is an optional field that describes the file store. 
"writeable" is a optional boolean field when given to a filestore will give it full access(read and write) . 
"state" indicates the state of the file store, following are the state and its description.
    * "DEPLOYMENT_PENDING" When the filestore is saved, its corresponding produced CFT is not deployed.
    * "DEPLOYED" Upon deployment of the CFT the state becomes DEPLOYED.
    * "ACTIVE" if all the configurations are in place.
    * "ERROR" if the accessrolearn is missing/wrong or the bucket is missing or wrong.
    * "UNKNOWN" when its old filestore and not tested.

"state" and "writeable" will be more useful once the new architecture is intergrated.

The fields that are allowed to be updated with the patch call:
    * name
    * description
    * bucket
    * accessRoleArn
    * storeType.fileFormat
    * folderPrefix

### Boto Retry config and explanation

We use standard retry mode with max maximum retry as 4.
[Explanation](https://botocore.amazonaws.com/v1/documentation/api/latest/reference/config.html)

Assuming an initial waiting time of 0.5 seconds (in actual is rand(0, 1), [reference](https://github.com/boto/botocore/blob/develop/botocore/retries/standard.py#L267))
and a total maximum of 4 retries with a base factor of 2 for the exponential backoff strategy,
and a maximum backoff time of 20 seconds, the total worst time it will take can be calculated as follows:

Lets Assume the Initial wait time to be 0.5 seconds
Retry 1: Wait 0.5 seconds
Retry 2: Wait 1.0 seconds (0.5 x 2)
Retry 3: Wait 2.0 seconds (1.0 x 2)
Retry 4: Wait 4.0 seconds (2.0 x 2)
The total worst time it will take for 4 retries with the given parameters is the sum of the waiting times for each retry:
0.5 + 1.0 + 2.0 + 4.0 = 7.5 seconds

Similarly, if Initial wait time is 0.9 seconds
Retry 1: Wait 0.9 seconds
Retry 2: Wait 1.8 seconds (0.9 x 2)
Retry 3: Wait 3.6 seconds (1.8 x 2)
Retry 4: Wait 7.2 seconds (3.6 x 2)
The total worst time it will take for 4 retries with the given parameters is the sum of the waiting times for each retry:
0.9 + 1.8 + 3.6 + 7.2 = 13.5 seconds



All the lambdas have a global timeout of 30 seconds.
This allows us to retry 3-4 failed boto calls 4 times before the lambda times out.
We should make not to make more than 3-4 boto calls in a single lambda
