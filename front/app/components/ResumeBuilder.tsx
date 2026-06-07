"use client";
import ReactMarkdown from "react-markdown";
import { useResources } from "@/lib/hooks/use-resources";
import { Button } from "./ui/button";
import { Printer } from "lucide-react";

export function ResumeBuilder() {
  const { resumeMarkdown } = useResources();

  const handlePrint = () => {
    window.print();
  };

  if (!resumeMarkdown) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-500 gap-4">
        <div className="text-xl">No resume draft yet.</div>
        <p>Tell the Agent: &quot;I want to create a resume for a [Job Title] position.&quot;</p>
      </div>
    );
  }

  return (
    <div className="h-full w-full bg-gray-100 p-8 overflow-y-auto relative">
      {/* Action Bar */}
      <div className="absolute top-4 right-8 print:hidden">
        <Button onClick={handlePrint} className="shadow-lg gap-2">
          <Printer className="w-4 h-4" /> Download/Print
        </Button>
      </div>

      {/* The Paper Document */}
      <div className="max-w-[21cm] mx-auto min-h-[29.7cm] bg-white shadow-2xl p-[2cm] print:shadow-none print:p-0 print:w-full print:max-w-none">
        <article className="prose prose-slate max-w-none prose-headings:font-serif prose-headings:text-slate-900 prose-li:marker:text-slate-500">
          <ReactMarkdown>{resumeMarkdown}</ReactMarkdown>
        </article>
      </div>
      
      {/* CSS for Print Mode to hide Chat/Sidebar/Map */}
      <style jsx global>{`
        @media print {
          body * {
            visibility: hidden;
          }
          /* Only show the markdown content */
          .prose, .prose * {
            visibility: visible;
          }
          .prose {
            position: absolute;
            left: 0;
            top: 0;
            width: 100%;
            margin: 0;
            padding: 2rem;
          }
          /* Hide Copilot Popup */
          .copilot-kit-popup, .copilot-popup-container {
            display: none !important;
          }
        }
      `}</style>
    </div>
  );
}
