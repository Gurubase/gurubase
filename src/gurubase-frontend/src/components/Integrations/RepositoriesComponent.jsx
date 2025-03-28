"use client";

import { useState, useEffect } from "react";
import { Input } from "@/components/ui/input";
import { getIntegrationChannels } from "@/app/actions";
import LoadingSkeleton from "@/components/Content/LoadingSkeleton";

const RepositoriesComponent = ({
  guruData,
  type,
  integrationData,
  selfhosted
}) => {
  const [repositories, setRepositories] = useState([]);
  const [repositoriesLoading, setRepositoriesLoading] = useState(true);
  const [internalError, setInternalError] = useState(null);

  useEffect(() => {
    const fetchRepositories = async () => {
      try {
        const repositoriesData = await getIntegrationChannels(
          guruData?.slug,
          type.toUpperCase()
        );

        console.log("repositoriesData", repositoriesData);
        if (repositoriesData?.error) {
          setInternalError(
            selfhosted
              ? "Failed to fetch repositories. Please make sure your bot token is correct."
              : "Failed to fetch repositories."
          );
        } else {
          setRepositories(repositoriesData?.channels || []);
          setInternalError(null);
        }
      } catch (err) {
        setInternalError(err.message);
      } finally {
        setRepositoriesLoading(false);
      }
    };

    fetchRepositories();
  }, [guruData?.slug, type, selfhosted]);

  if (repositoriesLoading) {
    return (
      <div className="p-6 guru-xs:p-2">
        <LoadingSkeleton
          count={2}
          width="100%"
          className="max-w-[400px] guru-xs:max-w-[280px] md:w-1/2"
        />
      </div>
    );
  }

  return (
    <div className="">
      <div className="flex flex-col gap-2">
        <h3 className="text-lg font-medium">Repositories</h3>
        <p className="text-[#6D6D6D] font-inter text-[14px] font-normal">
          The following repositories are connected to your Guru.
        </p>
      </div>
      {/* Repositories List */}
      <div className="space-y-4 guru-xs:mt-4 mt-5">
        {repositories
          .filter((repo) => repo.allowed)
          .map((repo) => (
            <div
              key={repo.id}
              className="flex md:items-center md:flex-row flex-col guru-xs:gap-4 gap-3 guru-xs:pt-1">
              <div className="relative w-full guru-xs:w-full guru-sm:w-[450px] guru-md:w-[300px] xl:w-[450px]">
                <span className="absolute left-3 top-2 text-xs font-normal text-gray-500">
                  Repository
                </span>
                <Input
                  readOnly
                  className="bg-gray-50 pt-8 pb-2"
                  value={repo.name}
                />
              </div>
            </div>
          ))}
      </div>
    </div>
  );
};

export default RepositoriesComponent;
